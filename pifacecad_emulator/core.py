import sys
from multiprocessing import Process, Queue
from threading import Barrier
from .gui import (
    run_emulator,
    get_col_row_from_value,
    get_value_from_col_row
)
import pifacecommon.mcp23s17
from pifacecommon.interrupts import (IODIR_ON, IODIR_OFF, IODIR_BOTH)
import pifacecad


# classes
class Switch(object):
    """An emulated switch on PiFace CAD."""
    def __init__(self, switch_num, cad):
        self.switch_num = switch_num
        self.cad = cad

    @property
    def value(self):
        cad.proc_comms_q_to_em.put(('get_switch', self.switch_num))
        return cad.proc_comms_q_from_em.get()


class SwitchPort(object):
    """An emulated switch port on PiFace CAD."""
    def __init__(self, cad):
        self.switches = [Switch(i, cad) for i in range(8)]

    @property
    def value(self):
        """Returns a numeric value of the switches."""
        onezero_switches = map(lambda x: 1 if x else 0, self.switches)
        v = 0
        for i, switch_value in enumerate(reversed(onezero_switches)):
            v |= switch_value << i
        return v


class PiFaceLCD(object):
    """An emulated PiFace CAD LCD."""
    def __init__(self, cad):
        self.cad = cad

    @property
    def viewport_corner(self):
        self.cad.proc_comms_q_to_em.put(('get_viewport_corner', 0))
        return self.cad.proc_comms_q_from_em.get()

    @viewport_corner.setter
    def viewport_corner(self, position):
        self.cad.proc_comms_q_to_em.put(('set_viewport_corner', position))

    def see_cursor(self):
        self.cad.proc_comms_q_to_em.put(('see_cursor', 0))

    def clear(self):
        self.cad.proc_comms_q_to_em.put(('clear', 0))

    def home(self):
        self.cad.proc_comms_q_to_em.put(('home', 0))

    def display_off(self):
        self.cad.proc_comms_q_to_em.put(('set_display_enable', 0))

    def display_on(self):
        self.cad.proc_comms_q_to_em.put(('set_display_enable', 1))

    def cursor_off(self):
        self.cad.proc_comms_q_to_em.put(('set_cursor_enable', 0))

    def cursor_on(self):
        self.cad.proc_comms_q_to_em.put(('set_cursor_enable', 1))

    def blink_off(self):
        self.cad.proc_comms_q_to_em.put(('set_blink_enable', 0))

    def blink_on(self):
        self.cad.proc_comms_q_to_em.put(('set_blink_enable', 1))

    def backlight_off(self):
        self.cad.proc_comms_q_to_em.put(('set_backlight_enable', 0))

    def backlight_on(self):
        self.cad.proc_comms_q_to_em.put(('set_backlight_enable', 1))

    # cursor or display shift
    def move_left(self):
        self.cad.proc_comms_q_to_em.put(('move_left', None))

    def move_right(self):
        self.cad.proc_comms_q_to_em.put(('move_right', None))

    def set_cursor(self, col, row):
        col_row = get_value_from_col_row(col, row)
        self.cad.proc_comms_q_to_em.put(('set_cursor', col_row))

    def get_cursor(self):
        self.cad.proc_comms_q_to_em.put(('get_cursor', 0))
        return proc_comms_q_from_em.get()

    def write(self, text):
        self.cad.proc_comms_q_to_em.put(('set_message', text))
        # print("q to em len", proc_comms_q_to_em.qsize())
    # not implemented
    # def left_to_right(self):
    # def right_to_left(self):
    # def right_justify(self):
    # def left_justify(self):
    # def colrow2address(self, col, row):
    # def send_command(self, command):
    # def send_data(self, data):
    # def send_byte(self, b):
    # def pulse_clock(self):
    # def write_custom_bitmap(self, char_bank, bitmap=None):
    # def store_custom_bitmap(self, char_bank, bitmap):
    # def char_bank_in_range_or_error():


class PiFaceCAD(object):
    """An emulated PiFace CAD."""
    def __init__(self):
        self.switch_port = SwitchPort(self)
        self.switches = [Switch(i, self) for i in range(pifacecad.NUM_SWITCHES)]
        self.lcd = PiFaceLCD(self)

        try:
            cad = pifacecad.PiFaceCAD()
        except pifacecommon.spi.SPIInitError as e:
            print("Error initialising PiFace CAD: ", e)
            print("Running without PiFace CAD.")
            cad = None

        self.proc_comms_q_to_em = Queue()
        self.proc_comms_q_from_em = Queue()

        emulator_sync = Barrier(2)
        # start the gui in another process
        self.emulator = Process(target=run_emulator,
                                args=(sys.argv,
                                      cad,
                                      self.proc_comms_q_to_em,
                                      self.proc_comms_q_from_em,
                                      emulator_sync))
        self.emulator.start()


class SwitchEventListener(object):
    """An emulated Switch event listener"""
    def __init__(self, arg):
        raise NotImplementedError("Switch Interrupts are not implemented in "
                                  "the emulator.")


class IREventListener(object):
    """An emulated IR event listener"""
    def __init__(self, arg):
        raise NotImplementedError("IR Interrupts are not implemented in the "
                                  "emulator.")


# def init():
#     try:
#         cad = pifacecad.PiFaceCAD()
#     except pifacecommon.core.InitError as e:
#         print("Error initialising PiFace CAD: ", e)
#         print("Running without PiFace CAD.")
#         cad = None

#     global proc_comms_q_to_em
#     global proc_comms_q_from_em
#     proc_comms_q_to_em = Queue()
#     proc_comms_q_from_em = Queue()

#     emulator_sync = Barrier(2)
#     # start the gui in another process
#     global emulator
#     emulator = Process(target=run_emulator, args=(
#         sys.argv, cad, proc_comms_q_to_em, proc_comms_q_from_em, emulator_sync
#     ))
#     emulator.start()
#     # print("core: waiting for sync")
#     # # emulator_sync.wait()
#     # assert proc_comms_q_from_em.get() == "setupcomplete"
#     # print("synced")


# def deinit():
#     # stop the gui
#     global proc_comms_q_to_em
#     proc_comms_q_to_em.put(('quit',))
#     global emulator
#     emulator.join()
