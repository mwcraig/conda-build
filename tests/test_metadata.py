import unittest
import os
import subprocess

from conda.resolve import MatchSpec

from conda_build.metadata import select_lines, handle_config_version


def test_select_lines():
    lines = """
test
test [abc] no

test [abc]
test # [abc]
test # [abc] yes
test # stuff [abc] yes
"""

    assert select_lines(lines, {'abc': True}) == """
test
test [abc] no

test
test
test
test
"""
    assert select_lines(lines, {'abc': False}) == """
test
test [abc] no

"""

class HandleConfigVersionTests(unittest.TestCase):

    def test_python(self):
        for spec, ver, res_spec in [
            ('python',       '3.4', 'python 3.4*'),
            ('python 2.7.8', '2.7', 'python 2.7.8'),
            ('python 2.7.8', '3.5', 'python 2.7.8'),
            ('python 2.7.8', None,  'python 2.7.8'),
            ('python',       None,  'python'),
            ('python x.x',   '2.7', 'python 2.7*'),
            ('python',       '27',  'python 2.7*'),
            ('python',        27,   'python 2.7*'),
            ]:
            ms = MatchSpec(spec)
            self.assertEqual(handle_config_version(ms, ver),
                             MatchSpec(res_spec))

        self.assertRaises(RuntimeError,
                          handle_config_version,
                          MatchSpec('python x.x'), None)

    def test_numpy(self):
        for spec, ver, res_spec, kwargs in [
            ('numpy',        None,  'numpy', {}),
            ('numpy',        18,    'numpy', {'dep_type': 'run'}),
            ('numpy',        18,    'numpy 1.8*', {'dep_type': 'build'}),
            ('numpy',        110,   'numpy', {}),
            ('numpy x.x',    17,    'numpy 1.7*', {}),
            ('numpy x.x',    110,   'numpy 1.10*', {}),
            ('numpy 1.9.1',  18,    'numpy 1.9.1', {}),
            ('numpy 1.9.0 py27_2', None,  'numpy 1.9.0 py27_2', {}),
            ]:
            ms = MatchSpec(spec)
            self.assertEqual(handle_config_version(ms, ver, **kwargs),
                             MatchSpec(res_spec))

        self.assertRaises(RuntimeError,
                          handle_config_version,
                          MatchSpec('numpy x.x'), None)
        self.assertRaises(RuntimeError,
                          handle_config_version,
                          MatchSpec('numpy x.x'), 19, dep_type='build')

    def test_numpy_version_pinned_in_build(self):
        # Version of numpy in build should be pinned by version in CONDA_NPY
        # if the runtime dependency is "numpy x.x". Is it?

        def subprocess_command_string(recipe_path):
            """
            Return a sequence of python commands that prints the numpy version
            specification from a recipe for use in a call to subprocess.
            """

            # Make list of python commands to be executed in subprocess.
            template = ['from conda_build.metadata import MetaData',
                        'meta = MetaData("{recipe_path}")',
                        'build_deps = meta.ms_depends("build")',
                        'numpy_spec = [b for b in build_deps if b.name == "numpy"][0]',
                        'print(numpy_spec)'
                        ]

            command = ';'.join(template).format(recipe_path=recipe_path)
            return command


        # Do NOT use the most recent version of numpy because if the version
        # is not being pinned properly the most version is what will be used
        # in the build environment.
        env_numpy_version = '1.9'

        # Set CONDA_NPY, then check build dependencies in a subprocess.
        os.environ['CONDA_NPY'] = env_numpy_version

        # In the first recipe build requirement is just 'numpy'.
        # In the second it is 'numpy >-1.7'.
        check_recipes = \
            ['test-recipes/metadata/numpy_build_run_xx',
             'test-recipes/metadata/numpy_build_run_xx_different_spec']

        for recipe in check_recipes:
            # Make metadata from the recipe below, which has runtime numpy
            # version 'numpy x.x' and build requirement 'numpy'.
            cmd = subprocess_command_string(recipe)
            numpy_spec = subprocess.check_output(['python', '-c', cmd])
            # Remove trailing \n
            numpy_spec = numpy_spec[:-1]
            numpy_spec = MatchSpec(numpy_spec)
            print(numpy_spec)
            # The resulting build dependency should be the value of the
            # environment variable CONDA_NPY
            self.assertEqual(numpy_spec,
                             MatchSpec('numpy {}*'.format(env_numpy_version)))
