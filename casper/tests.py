from django.test import LiveServerTestCase
from subprocess import Popen, PIPE
import os.path
import sys

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.views import serve
from django.utils.http import http_date
from django.conf import settings

__all__ = ['CasperTestCase']


def staticfiles_handler_serve(self, request):
    import time
    resp = serve(request, self.file_path(request.path), insecure=True)
    if resp.status_code == 200:
        resp["Expires"] = http_date(time.time() + 24 * 3600)
    return resp


class CasperTestCase(LiveServerTestCase):
    """LiveServerTestCase subclass that can invoke CasperJS tests."""

    use_phantom_disk_cache = False

    def __init__(self, *args, **kwargs):
        super(CasperTestCase, self).__init__(*args, **kwargs)
        if self.use_phantom_disk_cache:
            StaticFilesHandler.serve = staticfiles_handler_serve

    def casper_debug_opts(self, log_level='error'):
        """ Will output casper.log() messages with the log_level (one of `info`, `debug`, `warning', `error`) """
        debug_vals = {
        'verbose': 'true', 
        'log-level': '%s' % (getattr(settings, 'CASPERJS_LOG_LEVEL', log_level))
        }
        # other casperjs not test case specific kwargs.
        debug_vals.update(getattr(settings, 'CASPERJS_NON_TEST_SPECIFIC_OPTIONS', {}))
        return debug_vals

    def casper(self, test_filename, **kwargs):
        """CasperJS test invoker.

        Takes a test filename (.js) and optional arguments to pass to the
        casper test.

        Returns True if the test(s) passed, and False if any test failed.

        Since CasperJS startup/shutdown is quite slow, it is recommended
        to bundle all the tests from a test case in a single casper file
        and invoke it only once.
        """

        kwargs.update({
            'load-images': 'no',
            'disk-cache': 'yes' if self.use_phantom_disk_cache else 'no',
            'ignore-ssl-errors': 'yes',
            'url-base': self.live_server_url
        })

        # add casperjs debug args.
        kwargs.update(self.casper_debug_opts())

        cn = settings.SESSION_COOKIE_NAME
        if cn in self.client.cookies:
            kwargs['cookie-' + cn] = self.client.cookies[cn].value

        cmd = ['casperjs', 'test']

        cmd.extend([('--%s=%s' % (k,v)) if v else ('--%s' % k) for (k,v) in kwargs.iteritems()]) # check empty vals like in `--no-colors` option.
        cmd.append(test_filename)

        p = Popen(cmd, stdout=PIPE, stderr=PIPE,
            cwd=os.path.dirname(test_filename))  # flake8: noqa
        out, err = p.communicate()
        if p.returncode != 0:
            sys.stdout.write(out)
            sys.stderr.write(err)
        return p.returncode == 0
