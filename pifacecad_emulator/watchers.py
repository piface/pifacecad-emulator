from PySide.QtCore import (QThread, QObject, Slot, Signal)
import threading
import pifacecad
from time import sleep


class Blinker(QObject):
    """Blinks the blinker on the emulator."""

    blink_signal = Signal()

    def __init__(self, emu_window, blinker_start):
        super(Blinker, self).__init__()
        self.emu_window = emu_window
        self.blinker_start = blinker_start

    def blink(self):
        # print("cursor blinker started")
        self.blinker_start.wait()
        while True:
            sleep(1)
            self.blink_signal.emit()


class InterfaceMessageHandler(QObject):
    """Handles the queue which talks to the main process."""

    set_message = Signal(str)
    set_cursor = Signal(int)
    set_viewport_corner = Signal(int)
    set_display_enable = Signal(int)
    set_backlight_enable = Signal(int)
    set_cursor_enable = Signal(int)
    set_blink_enable = Signal(int)
    get_switch = Signal(int)
    get_cursor = Signal(int)
    get_viewport_corner = Signal(int)
    move_left = Signal(int)
    move_right = Signal(int)
    home = Signal(int)
    clear = Signal(int)
    see_cursor = Signal(int)

    def __init__(self, app, q_to_em, q_from_em, handler_start):
        super(InterfaceMessageHandler, self).__init__()
        self.main_app = app
        self.q_to_em = q_to_em
        self.q_from_em = q_from_em
        self.signals = {
            'set_message': self.set_message,
            'set_cursor': self.set_cursor,
            'set_viewport_corner': self.set_viewport_corner,
            'set_display_enable': self.set_display_enable,
            'set_backlight_enable': self.set_backlight_enable,
            'set_cursor_enable': self.set_cursor_enable,
            'set_blink_enable': self.set_blink_enable,
            'get_switch': self.get_switch,
            'get_cursor': self.get_cursor,
            'get_viewport_corner': self.get_viewport_corner,
            'move_left': self.move_left,
            'move_right': self.move_right,
            'home': self.home,
            'clear': self.clear,
            'see_cursor': self.see_cursor,
            # 'quit': self.quit_main_app,
        }
        self.handler_start = handler_start

    def check_queue(self):
        self.handler_start.wait()
        while True:
            # print("trying for action")
            action = self.q_to_em.get()
            # print("got action", action)
            task = action[0]
            if task == 'quit':
                self.main_app.quit()
            else:
                try:
                    data = action[1]
                except IndexError:
                    data = None
                self.signals[task].emit(data)

    @Slot(int)
    def send_get_switch_result(self, value):
        self.q_from_em.put(value)

    @Slot(int)
    def send_get_cursor_result(self, value):
        col, row = get_col_row_from_value(value)
        self.q_from_em.put((col, row))

    @Slot(int)
    def send_get_viewport_corner_result(self, value):
        self.q_from_em.put(value)


class SwitchWatcher(QObject):
    """Watches switches and changes the emulator accordingly."""

    set_switch_enable = Signal(int)
    set_switch_disable = Signal(int)

    def __init__(self):
        super().__init__()
        self.event_listener = pifacecad.SwitchEventListener()
        for i in range(8):
            self.event_listener.register(
                i, pifacecad.IODIR_BOTH, self.set_input)

    def check_inputs(self):
        self.event_listener.activate()
        # print("switch watcher: activated")

    def stop_checking_inputs(self):
        self.event_listener.deactivate()
        # print("switch watcher: deactivated")

    def set_input(self, event):
        # print("switch watcher: event detected")
        if event.direction == pifacecad.IODIR_ON:
            self.set_switch_enable.emit(event.pin_num)
        else:
            self.set_switch_disable.emit(event.pin_num)


def start_blinker(app, emu_window):
    # need to spawn a worker thread that watches the proc_comms_q
    # need to seperate queue function from queue thread
    # http://stackoverflow.com/questions/4323678/threading-and-signals-problem
    # -in-pyqt
    blinker_start = threading.Barrier(2)
    blinker = Blinker(emu_window, blinker_start)
    blinker_thread = QThread()
    blinker.moveToThread(blinker_thread)
    blinker_thread.started.connect(blinker.blink)

    blinker.blink_signal.connect(emu_window.blink)

    # not sure why this doesn't work by connecting to blinker_thread.quit
    def about_to_quit():
        blinker_thread.quit()
    app.aboutToQuit.connect(about_to_quit)

    blinker_thread.start()
    blinker_start.wait()


def start_interface_message_handler(
        app, emu_window, proc_comms_q_to_em, proc_comms_q_from_em):
    # need to spawn a worker thread that watches the proc_comms_q
    # need to seperate queue function from queue thread
    # http://stackoverflow.com/questions/4323678/threading-and-signals-problem
    # -in-pyqt
    handler_start = threading.Barrier(2)
    intface_msg_hand = InterfaceMessageHandler(
        app, proc_comms_q_to_em, proc_comms_q_from_em, handler_start)
    intface_msg_hand_thread = QThread()
    intface_msg_hand.moveToThread(intface_msg_hand_thread)
    intface_msg_hand_thread.started.connect(intface_msg_hand.check_queue)

    # now that we've set up the thread, let's set up rest of signals/slots
    intface_msg_hand.set_viewport_corner.connect(
        emu_window.slot_set_viewport_corner)
    intface_msg_hand.set_cursor.connect(emu_window.slot_set_cursor)
    intface_msg_hand.set_message.connect(emu_window.slot_set_message)
    intface_msg_hand.set_display_enable.connect(
        emu_window.slot_set_display_enable)
    intface_msg_hand.set_backlight_enable.connect(
        emu_window.slot_set_backlight_enable)
    intface_msg_hand.set_cursor_enable.connect(
        emu_window.slot_set_cursor_enable)
    intface_msg_hand.set_blink_enable.connect(
        emu_window.slot_set_blink_enable)
    intface_msg_hand.get_switch.connect(emu_window.slot_get_switch)
    intface_msg_hand.get_cursor.connect(emu_window.slot_get_cursor)
    intface_msg_hand.get_viewport_corner.connect(
        emu_window.slot_get_viewport_corner)
    intface_msg_hand.move_left.connect(emu_window.slot_move_left)
    intface_msg_hand.move_right.connect(emu_window.slot_move_right)
    intface_msg_hand.home.connect(emu_window.slot_home)
    intface_msg_hand.clear.connect(emu_window.slot_clear)
    intface_msg_hand.see_cursor.connect(emu_window.slot_see_cursor)

    emu_window.send_switch.connect(intface_msg_hand.send_get_switch_result)
    emu_window.send_cursor.connect(intface_msg_hand.send_get_cursor_result)
    emu_window.send_viewport_corner.connect(
        intface_msg_hand.send_get_viewport_corner_result)

    def about_to_quit():
        intface_msg_hand_thread.quit()
    app.aboutToQuit.connect(about_to_quit)

    intface_msg_hand_thread.start()
    handler_start.wait()


def start_switch_watcher(app, emu_window):
    switch_watcher = SwitchWatcher()
    switch_watcher.set_switch_enable.connect(emu_window.set_switch_enable)
    switch_watcher.set_switch_disable.connect(emu_window.set_switch_disable)
    app.aboutToQuit.connect(switch_watcher.stop_checking_inputs)
    switch_watcher.check_inputs()


# have to reimplement because circular dependent imports
LCD_RAM_WIDTH = 80


def get_col_row_from_value(value):
    row = int(value / LCD_RAM_WIDTH)
    col = value - (LCD_RAM_WIDTH * row)
    return col, row


def get_value_from_col_row(col, row):
    return col + (LCD_RAM_WIDTH * row)
