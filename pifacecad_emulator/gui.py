from PySide.QtCore import (QThread, QObject, Slot, Signal)
from PySide.QtGui import (
    QMainWindow,
    QPushButton,
    QApplication,
    QPainter,
    QFont
)
from time import sleep
import threading
# from .watchers import (start_interface_message_handler, start_switch_watcher)
from .pifacecad_emulator_ui import Ui_pifaceCADEmulatorWindow
from .watchers import (
    start_blinker,
    start_interface_message_handler,
    start_switch_watcher,
)
import pifacecad


COL_PIXEL = (39, 49, 59, 69, 79, 89, 99, 109, 119, 129, 139, 149, 159,
             169, 179, 189)
ROW_PIXEL = (80, 101)

LCD_LINES = 2
LCD_WIDTH = 16
LCD_RAM_WIDTH = 80
LCD_ROW_WIDTH = int(80 / 2)


class PiFaceCADEmulatorWindow(QMainWindow, Ui_pifaceCADEmulatorWindow):
    def __init__(self, parent=None):
        super(PiFaceCADEmulatorWindow, self).__init__(parent)
        self.setupUi(self)

        self._blink_hidden_state = False
        self.cad = None

        # self.switch_state = [False for i in range(8)]
        self._cursor_position = [0, 0]
        self.clear()

        self.switch_buttons = [self.switch0Button,
                               self.switch1Button,
                               self.switch2Button,
                               self.switch3Button,
                               self.switch4Button,
                               self.switch5Button,
                               self.switch6Button,
                               self.switch7Button]

        for button in self.switch_buttons:
            button.pressed.connect(self.switch_pressed)
            button.released.connect(self.switch_released)

        self.displayCheckBox.stateChanged.connect(self.change_display)
        self.backlightCheckBox.stateChanged.connect(self.change_backlight)
        self.cursorCheckBox.stateChanged.connect(self.change_cursor)
        self.blinkCheckBox.stateChanged.connect(self.change_blink)

        self.homeButton.clicked.connect(self.home)
        self.clearButton.clicked.connect(self.clear)

        self.writeMessageLineEdit.returnPressed.connect(self.write_message)
        self.writeMessagePushButton.clicked.connect(self.write_message)

        self.cursorColumnLineEdit.returnPressed.connect(self.move_cursor)
        self.cursorRowLineEdit.returnPressed.connect(self.move_cursor)
        self.gotoColRowButton.clicked.connect(self.move_cursor)
        self.seeCursorButton.clicked.connect(self.see_cursor)

        self.viewportColumnLineEdit.returnPressed.connect(self.goto_viewport)
        self.gotoViewportButton.clicked.connect(self.goto_viewport)
        self.moveLeftPushButton.clicked.connect(self.move_left)
        self.moveRightPushButton.clicked.connect(self.move_right)

        # self.flush_lcd_lines()
        self.viewport_corner = 0

    def switch_pressed(self):
        self.switch_pressed_or_released()

    def switch_released(self):
        self.switch_pressed_or_released()

    def switch_pressed_or_released(self):
        """Need to call registered functions."""
        # print("a switch was pressed/released")
        pass

    @property
    def switch_state(self):
        """Returns a list of switch values."""
        if self.cad is None:
            return [switch.isDown() for switch in self.switch_buttons]
        else:
            return [switch.value == 1 for switch in self.cad.switches]

    def change_display(self, state):
        if state:
            self.display_on()
        else:
            self.display_off()

    def change_backlight(self, state):
        if state:
            self.backlight_on()
        else:
            self.backlight_off()

    def change_cursor(self, state):
        if state:
            self.cursor_on()
        else:
            self.cursor_off()

    def change_blink(self, state):
        if state:
            self.blink_on()
        else:
            self.blink_off()

    def move_cursor(self):
        try:
            col = int(self.cursorColumnLineEdit.text())
        except ValueError:
            col = 0
            self.cursorColumnLineEdit.setText(str(col))
        try:
            row = int(self.cursorRowLineEdit.text())
        except ValueError:
            row = 0
            self.cursorRowLineEdit.setText(str(row))
        self.set_cursor(col, row)
        self.cursorColumnLineEdit.setFocus()
        self.cursorColumnLineEdit.setSelection(0, len(str(col)))

    def see_cursor(self):
        if self.cad:
            self.cad.lcd.see_cursor()
            self._viewport_corner = self.cad.lcd.viewport_corner
            self.flush_lcd_lines()
            self.update_cursor_and_blink()
        else:
            while not self.cursorLabel.isVisible():
                self._viewport_corner = \
                    (self._viewport_corner + 1) % LCD_ROW_WIDTH
                self.flush_lcd_lines()
                self.update_cursor_label()

    def goto_viewport(self):
        try:
            self.viewport_corner = int(self.viewportColumnLineEdit.text())
        except ValueError:
            self.viewport_corner = 0
            self.viewportColumnLineEdit.setText('0')

        self.viewportColumnLineEdit.setFocus()
        self.viewportColumnLineEdit.setSelection(
            0, len(str(self.viewport_corner)))

    def move_left(self):
        self.viewport_corner -= 1

    def move_right(self):
        self.viewport_corner += 1

    def home(self):
        if self.cad:
            self.cad.lcd.home()
        self.viewport_corner = 0
        self._set_virtual_cursor(0, 0)

    def clear(self):
        if self.cad:
            self.cad.lcd.clear()
        self.lcd_lines = [" "*LCD_ROW_WIDTH, " "*LCD_ROW_WIDTH]
        self.viewport_corner = 0
        self._set_virtual_cursor(0, 0)

    @property
    def viewport_corner(self):
        return self._viewport_corner

    @viewport_corner.setter
    def viewport_corner(self, value):
        self._viewport_corner = value % LCD_ROW_WIDTH
        if self.cad:
            self.cad.lcd.viewport_corner = self._viewport_corner
        self.flush_lcd_lines()
        self.update_cursor_and_blink()

    def display_on(self):
        if self.cad:
            self.cad.lcd.display_on()
        self.lcdLine0Label.setVisible(True)
        self.lcdLine1Label.setVisible(True)
        self.displayCheckBox.setChecked(True)
        self.update_cursor_and_blink()

    def display_off(self):
        if self.cad:
            self.cad.lcd.display_off()
        self.lcdLine0Label.setVisible(False)
        self.lcdLine1Label.setVisible(False)
        self.displayCheckBox.setChecked(False)
        self.update_cursor_and_blink()

    def backlight_on(self):
        if self.cad:
            self.cad.lcd.backlight_on()
        self.backlightLabel.setVisible(True)
        self.backlightCheckBox.setChecked(True)

    def backlight_off(self):
        if self.cad:
            self.cad.lcd.backlight_off()
        self.backlightLabel.setVisible(False)
        self.backlightCheckBox.setChecked(False)

    def set_cursor(self, col, row):
        if self.cad:
            self.cad.lcd.set_cursor(col, row)
        self._set_virtual_cursor(col, row)

    def get_cursor(self):
        if self.cad:
            col, row = self.cad.lcd.get_cursor()
            self._set_virtual_cursor(col, row)
        return tuple(self._cursor_position)

    def _set_virtual_cursor(self, col, row):
        row %= (LCD_LINES - 1)
        self._cursor_position = [col, row]
        self.update_cursor_and_blink()

    def update_cursor_and_blink(self):
        self.update_cursor_label()
        self.update_blink_label()

    def update_cursor_label(self):
        col, row = self.get_cursor_label_col_row()
        visible = self._cursor_is_visible()
        self.cursorLabel.setVisible(visible)
        if visible:
            # print("trying {},{}".format(col, row))
            self.cursorLabel.move(COL_PIXEL[col], ROW_PIXEL[row])

    def update_blink_label(self):
        col, row = self.get_cursor_label_col_row()
        visible = self._blink_is_visible()
        self.blinkLabel.setVisible(visible)
        if visible:
            self.blinkLabel.move(COL_PIXEL[col], ROW_PIXEL[row])

    def get_cursor_label_col_row(self):
        col, row = self._cursor_position
        if self._is_wrap_around():
            # add the difference to the column to shift it
            col = LCD_ROW_WIDTH - self.viewport_corner
        else:
            col -= self.viewport_corner
        return col, row

    def _is_wrap_around(self):
        col, row = self._cursor_position
        # print("vpc-col", self.viewport_corner-col)
        # print("threshold", LCD_RAM_WIDTH-LCD_WIDTH)
        return (self.viewport_corner - col) > (LCD_ROW_WIDTH - LCD_WIDTH)

    def _cursor_is_visible(self):
        cursor_on_screen = self._cursor_is_on_screen()
        display_on = self.displayCheckBox.isChecked()
        cursor_on = self.cursorCheckBox.isChecked()
        # print("cursor_on_screen", cursor_on_screen)
        # print("display_on", display_on)
        # print("cursor_on", cursor_on)
        return cursor_on_screen and display_on and cursor_on

    def _blink_is_visible(self):
        blink_on_screen = self._cursor_is_on_screen()
        display_on = self.displayCheckBox.isChecked()
        blink_on = self.blinkCheckBox.isChecked()
        hidden = self._blink_hidden_state
        # print("blink_on_screen", blink_on_screen)
        # print("display_on", display_on)
        # print("blink_on", blink_on)
        return blink_on_screen and display_on and blink_on and not hidden

    def _cursor_is_on_screen(self):
        col, row = self._cursor_position
        too_far_right = col >= (self.viewport_corner + LCD_WIDTH)
        too_far_left = col < self.viewport_corner
        can_see_from_wrap_around = \
            (LCD_ROW_WIDTH + col) < (self.viewport_corner + LCD_WIDTH)
        # print("col", col)
        # print("too_far_right", too_far_right)
        # print("too_far_left{}, ({}, {})".format(too_far_left, col, row))
        # print("vpc", self.viewport_corner)
        # print("can_see_from_wrap_around", can_see_from_wrap_around)
        # print("LCD_RAM_WIDTH+col", LCD_RAM_WIDTH+col)
        # print("vpc+LCD_WIDTH", self.viewport_corner+LCD_WIDTH)
        return (not (too_far_right or too_far_left)) or \
            can_see_from_wrap_around

    def cursor_on(self):
        if self.cad:
            self.cad.lcd.cursor_on()
        self.cursorLabel.setVisible(True)
        self.cursorCheckBox.setChecked(True)

    def cursor_off(self):
        if self.cad:
            self.cad.lcd.cursor_off()
        self.cursorLabel.setVisible(False)
        self.cursorCheckBox.setChecked(False)

    def blink_on(self):
        if self.cad:
            self.cad.lcd.blink_on()
        self.blinkLabel.setVisible(True)
        self.blinkCheckBox.setChecked(True)

    def blink_off(self):
        if self.cad:
            self.cad.lcd.blink_off()
        self.blinkLabel.setVisible(False)
        self.blinkCheckBox.setChecked(False)

    def blink(self):
        self._blink_hidden_state = not self._blink_hidden_state
        self.update_blink_label()
        # if self.displayCheckBox.isChecked() and \
        #         self.blinkCheckBox.isChecked():
        #     self.blinkLabel.setVisible(not self.blinkLabel.isVisible())

    def write_message(self, message=None):
        if message is None:
            message = self.writeMessageLineEdit.text()
        # print("Writing message:", message)
        col, row = self.get_cursor()
        lines = message.split("\\n")

        # first row
        pre = self.lcd_lines[row][:col]
        new_col = col + len(lines[0])
        post = self.lcd_lines[row][new_col:]
        self.lcd_lines[row] = "{}{}{}".format(pre, lines[0], post)
        new_row = row

        # second row
        if len(lines) > 1:
            col = 0  # new line starts from the beginning
            new_col = col+len(lines[1])
            new_row = 1
            #pre = self.lcd_lines[1][:col]
            post = self.lcd_lines[new_row][new_col:]
            self.lcd_lines[new_row] = "{}{}".format(lines[1], post)

        self.flush_lcd_lines()
        if self.cad:
            self.cad.lcd.write(message.replace("\\n", "\n"))
            col, row = self.cad.lcd.get_cursor()
            self._set_virtual_cursor(col, row)
        else:
            print("setting vc, col {}, row {}".format(new_col, new_row))
            self._set_virtual_cursor(new_col, new_row)

    def flush_lcd_lines(self):
        start = self.viewport_corner
        end = self.viewport_corner+LCD_WIDTH

        # need to support wrapping around
        # concatenate line with itself and pretend to wrap around
        top_line = self.lcd_lines[0] + self.lcd_lines[0]
        self.lcdLine0Label.setText(top_line[start:end])
        bottom_line = self.lcd_lines[1] + self.lcd_lines[1]
        self.lcdLine1Label.setText(bottom_line[start:end])

    @Slot(str)
    def slot_set_message(self, message):
        self.write_message(message)

    @Slot(int)
    def slot_set_cursor(self, value):
        col, row = get_col_row_from_value(value)
        self.set_cursor(col, row)

    @Slot(int)
    def slot_set_viewport_corner(self, value):
        self.viewport_corner = value

    send_viewport_corner = Signal(int)

    @Slot(int)
    def slot_get_viewport_corner(self, data):
        self.send_viewport_corner.emit(data)

    @Slot(int)
    def slot_set_display_enable(self, value):
        if value == 1:
            self.display_on()
        else:
            self.display_off()

    @Slot(int)
    def slot_set_backlight_enable(self, value):
        if value == 1:
            self.backlight_on()
        else:
            self.backlight_off()

    @Slot(int)
    def slot_set_cursor_enable(self, value):
        if value == 1:
            self.cursor_on()
        else:
            self.cursor_off()

    @Slot(int)
    def slot_set_blink_enable(self, value):
        if value == 1:
            self.blink_on()
        else:
            self.blink_off()

    send_switch = Signal(int)

    @Slot(int)
    def slot_get_switch(self, switch_num):
        self.send_switch.emit(1 if self.switch_state[switch_num] else 0)

    @Slot(int)
    def set_switch_enable(self, switch_num):
        # print("emulator: checking switch", switch_num)
        self.switch_buttons[switch_num].setChecked(True)

    @Slot(int)
    def set_switch_disable(self, switch_num):
        # print("emulator: unchecking switch", switch_num)
        self.switch_buttons[switch_num].setChecked(False)

    @Slot(int)
    def slot_move_left(self, data):
        self.move_left()

    @Slot(int)
    def slot_move_right(self, data):
        self.move_right()

    send_cursor = Signal(int)

    @Slot(int)
    def slot_get_cursor(self, data):
        col, row = self.get_cursor()
        value = get_value_from_col_row(col, row)
        self.send_cursor.emit(value)

    @Slot(int)
    def slot_home(self, data):
        self.home()

    @Slot(int)
    def slot_clear(self, data):
        self.clear()

    @Slot(int)
    def slot_see_cursor(self, data):
        self.see_cursor()


def run_emulator(
        sysargv,
        cad,
        proc_comms_q_to_em,
        proc_comms_q_from_em,
        emulator_sync):
    app = QApplication(sysargv)

    emu_window = PiFaceCADEmulatorWindow()
    emu_window.cad = cad
    # now we have to set up some state so that the emulator and the cad are in
    #sync
    emu_window.display_on()
    emu_window.cursor_on()
    emu_window.backlight_off()
    emu_window.blink_on()

    start_interface_message_handler(
        app, emu_window, proc_comms_q_to_em, proc_comms_q_from_em)

    # only watch switches if there is actually a piface cad attached
    if emu_window.cad is not None:
        start_switch_watcher(app, emu_window)

    start_blinker(app, emu_window)  # causing problems

    emu_window.show()
    app.exec_()


def get_col_row_from_value(value):
    row = int(value / LCD_ROW_WIDTH)
    col = value - (LCD_ROW_WIDTH * row)
    return col, row


def get_value_from_col_row(col, row):
    return col + (LCD_ROW_WIDTH * row)
