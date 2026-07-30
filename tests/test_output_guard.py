import unittest

from token_saver.output_guard import validate_output


class OutputGuardTests(unittest.TestCase):
    def test_exact_words(self):
        self.assertTrue(validate_output("one two three", exact_words=3).valid)
        self.assertFalse(validate_output("one two", exact_words=3).valid)

    def test_json(self):
        self.assertTrue(validate_output('{"ok": true}', require_json=True).valid)
        self.assertFalse(validate_output('{bad}', require_json=True).valid)

    def test_bullets(self):
        text = "- one\n- two\n- three\n"
        self.assertTrue(validate_output(text, exact_bullets=3).valid)


if __name__ == "__main__":
    unittest.main()
