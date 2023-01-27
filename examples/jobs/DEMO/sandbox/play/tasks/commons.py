from vortex import toolbox
from vortex.layout.jobs import JobAssistantPlugin
from vortex.layout.nodes import Task


class ConfigFileAccessJobAssistantPlugin(JobAssistantPlugin):
    """
    Look in the configuration file and export entries starting
    with "useless" (if any).
    """

    _footprint = dict(
        info = 'JobAssistant Configuration File Access Plugin',
        attr = dict(
            kind = dict(
                values = ['configfile_access', ]
            ),
        ),
    )

    def plugable_env_setup(self, t, **kw):  # @UnusedVariable
        """Customise the environment variables."""
        t.sh.highlight('Configuration File Access Plugin')
        todo = {k: v
                for k, v in self.masterja.conf.items()
                if k.startswith('useless')}
        if todo:
            for k, v in sorted(todo.items()):
                print('Exporting {:s} to the environment (value={!s})'.format(k, v))
                t.env[k] = v
        else:
            print('Nothing to export.')


class Beacon(Task):
    """Generate a JSON file and store it."""

    def process(self):

        if 'compute' in self.steps:

            self.sh.subtitle('Creating the AlgoComponent')
            tbalgo = toolbox.algo(
                kind = 'play_beacon',
                engine = 'algo',
                identifier = self.tag,
                member = self.conf.member,
                failer = self.conf.get('failer', None)
            )
            self.sh.highlight('Running the AlgoComponent')
            self.component_runner(tbalgo)

        if 'late-backup' in self.steps:

            toolbox.output(
                role = "Beacon",
                kind = "beacon",
                namespace = self.conf.fullspace,
                experiment = self.conf.xpid,
                member = self.conf.member,
                block = self.config_tag,
                local = 'the_file.json',
                format = 'json',
            )
