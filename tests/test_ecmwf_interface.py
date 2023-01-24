from unittest import TestCase, main

from ecmwf.tools.interfaces import ECMWFInterface
from vortex import ticket

sh = ticket().sh


class TestPrepareArguments(TestCase):

    def _check_result_test(self, command, expected_command,
                           list_args, expected_list_args,
                           dict_args, expected_dict_args,
                           list_options, expected_list_options):
        self.assertEqual(command, expected_command)
        self.assertListEqual(list_args, expected_list_args)
        self.assertDictEqual(dict_args, expected_dict_args)
        self.assertListEqual(list_options, expected_list_options)

    def test_command_interface_true(self):
        interface = ECMWFInterface(system=sh, command="ecmwf", command_interface=True)
        # Test 1
        test_command_line = "ecfs.py ecp -i toto.txt titi.txt -value=toto,tata -m -target=toto2.txt".split()
        command, list_args, dict_args, list_options = interface.prepare_arguments(test_command_line)
        self._check_result_test(command, "ecp",
                                list_args, ["toto.txt", "titi.txt"],
                                dict_args, {"value": ["toto", "tata"], "target": "toto2.txt"},
                                list_options, ["i", "m"])
        # Test 2
        test_command_line = "ecfs.py ecp -i -value=toto,tata".split()
        command, list_args, dict_args, list_options = interface.prepare_arguments(test_command_line)
        self._check_result_test(command, "ecp",
                                list_args, list(),
                                dict_args, {"value": ["toto", "tata"], },
                                list_options, ["i", ])
        # Test 2
        test_command_line = "ecfs.py -i -value=toto".split()
        command, list_args, dict_args, list_options = interface.prepare_arguments(test_command_line)
        self._check_result_test(command, None,
                                list_args, list(),
                                dict_args, {"value": "toto", },
                                list_options, ["i", ])

    def test_command_interface_false(self):
        interface = ECMWFInterface(system=sh, command="ecmwf", command_interface=False)
        # Test 1
        test_command_line = "ecfs.py ecp -i toto.txt titi.txt -value=toto,tata -m -target=toto2.txt".split()
        command, list_args, dict_args, list_options = interface.prepare_arguments(test_command_line)
        self._check_result_test(command, None,
                                list_args, ["ecp", "toto.txt", "titi.txt"],
                                dict_args, {"value": ["toto", "tata"], "target": "toto2.txt"},
                                list_options, ["i", "m"])
        # Test 2
        test_command_line = "ecfs.py ecp -i -value=toto,tata".split()
        command, list_args, dict_args, list_options = interface.prepare_arguments(test_command_line)
        self._check_result_test(command, None,
                                list_args, ["ecp", ],
                                dict_args, {"value": ["toto", "tata"], },
                                list_options, ["i", ])
        # Test 3
        test_command_line = "ecfs.py -i -value=toto".split()
        command, list_args, dict_args, list_options = interface.prepare_arguments(test_command_line)
        self._check_result_test(command, None,
                                list_args, list(),
                                dict_args, {"value": "toto", },
                                list_options, ["i", ])


class TestBuildCommandLine(TestCase):

    def test_build_commandline(self):
        interface = ECMWFInterface(system=sh, command="ecmwf", command_interface=True)
        # Test 1
        command = "ecmwf"
        list_args = list()
        dict_args = {"target": "titi"}
        list_options = list()
        command_line = interface.build_command_line(command, list_args, dict_args, list_options)
        self.assertEqual(command_line, "ecmwf -target titi")
        # Test 2
        command = "ecmwf"
        list_args = ["toto.txt", "titi.txt"]
        dict_args = {"value": ["titi1", "titi2"]}
        list_options = ["u", "verbose", "r"]
        command_line = interface.build_command_line(command, list_args, dict_args, list_options)
        self.assertEqual(command_line, "ecmwf -value titi1 titi2 -u -verbose -r toto.txt titi.txt")

    def test_actual_command(self):
        interface = ECMWFInterface(system=sh, command="ecmwf", command_interface=True)
        self.assertEqual(interface.actual_command('toto'), 'toto')
        self.assertEqual(interface.actual_command(), 'ecmwf')


if __name__ == "main":
    main(verbosity=2)
