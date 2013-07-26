#!/usr/bin/env python3
import sys
import unittest
import threading
import pifacecad_emulator
from time import sleep


PY3 = sys.version_info.major >= 3
if not PY3:
    input = raw_input

    from time import sleep

    class Barrier(object):
        def __init__(self, n, timeout=None):
            self.count = 0
            self.n = n
            self.timeout = timeout

        def wait(self):
            self.count += 1
            while self.count < self.n:
                sleep(0.0001)

    threading.Barrier = Barrier


class TestInterface(unittest.TestCase):
    def setUp(self):
        pifacecad_emulator.init()
        self.cad = pifacecad_emulator.PiFaceCAD()

    def test_lcd(self):
        self.cad.lcd.write("hello")
        self.assertTrue(yes_no_question("Is the LCD displaying 'hello'?"))

    def test_viewport_corner(self):
        test_word = "onomatopoeia"
        self.cad.lcd.clear()
        self.cad.lcd.write(test_word)

        shift_amount = 3
        self.cad.lcd.viewport_corner = shift_amount
        self.assertTrue(yes_no_question(
            "Is '{}' written on the display".format(test_word[shift_amount:])))

        shift_amount = -1
        self.cad.lcd.viewport_corner = shift_amount
        self.assertTrue(yes_no_question(
            "Is '{}' written on the display".format(" "+test_word)))

    def test_see_cursor(self):
        test_word = "*EXPLOSION*"
        self.cad.lcd.clear()
        self.cad.lcd.write(test_word)
        self.cad.lcd.set_cursor(20, 0)
        self.cad.lcd.see_cursor()
        self.assertTrue(yes_no_question("Is the cursor on the display?"))

    def test_clear(self):
        self.cad.lcd.write("abracadabra")
        self.cad.lcd.clear()
        self.assertTrue(yes_no_question("Is the display clear?"))

    def test_home(self):
        col, row = 5, 1
        self.cad.lcd.set_cursor(col, row)
        self.cad.lcd.home()
        self.assertTrue(yes_no_question("Is the cursor at (0, 0)?"))

    def test_move_right_left(self):
        test_word = "spam"
        self.cad.lcd.clear()
        self.cad.lcd.write(test_word)
        self.cad.lcd.move_right()
        self.assertTrue(yes_no_question(
            "Is '{}' written on the display".format(test_word[1:])))
        self.cad.lcd.move_left()
        self.assertTrue(yes_no_question(
            "Is '{}' written on the display".format(test_word)))
        self.cad.lcd.move_left()
        self.assertTrue(yes_no_question(
            "Is '{}' written on the display".format(" "+test_word)))

    def test_set_and_get_cursor(self):
        col, row = 5, 1
        self.cad.lcd.set_cursor(col, row)
        self.assertTrue(yes_no_question(
            "Is the cursor at ({}, {})?".format(col, row)))
        self.assertTrue(self.cad.lcd.get_cursor() == (col, row))

    def test_backlight_blink_cursor_display(self):
        self.cad.lcd.backlight_off()
        self.assertTrue(yes_no_question("Is the backlight off?"))
        self.cad.lcd.backlight_on()
        self.assertTrue(yes_no_question("Is the backlight on?"))

        self.cad.lcd.blink_off()
        self.assertTrue(yes_no_question("Is the blink off?"))
        self.cad.lcd.blink_on()
        self.assertTrue(yes_no_question("Is the blink on?"))

        self.cad.lcd.cursor_off()
        self.assertTrue(yes_no_question("Is the cursor off?"))
        self.cad.lcd.cursor_on()
        self.assertTrue(yes_no_question("Is the cursor on?"))

        self.cad.lcd.display_off()
        self.assertTrue(yes_no_question("Is the display off?"))
        self.cad.lcd.display_on()
        self.assertTrue(yes_no_question("Is the display on?"))

    def tearDown(self):
        self.cad.lcd.clear()
        pifacecad_emulator.deinit()


def yes_no_question(question):
    answer = input("{} [Y/n] ".format(question))
    correct_answers = ("y", "yes", "Y", "")
    return answer in correct_answers


if __name__ == "__main__":
    unittest.main()
