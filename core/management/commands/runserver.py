import os
import threading
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen

from django.core.management.commands.runserver import Command as BaseRunserverCommand


class Command(BaseRunserverCommand):
    help = (
        'Starts the development server and opens API documentation in the browser.'
    )

    def on_bind(self, server_port):
        super().on_bind(server_port)

        host = self._docs_host()
        docs_url = f'http://{host}:{server_port}/api/docs/'

        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO(f'Documentation: {docs_url}'))
        self.stdout.write('')

        if self._should_open_browser():
            threading.Thread(
                target=self._open_browser_when_ready,
                args=(docs_url,),
                daemon=True,
            ).start()

    def _docs_host(self):
        if self._raw_ipv6:
            return f'[{self.addr}]'
        if self.addr in ('0', '0.0.0.0', ''):
            return '127.0.0.1'
        return self.addr

    def _should_open_browser(self):
        if os.environ.get('RUN_MAIN') != 'true':
            return False
        return os.environ.get('DJANGO_DOCS_AUTO_OPEN', '1') != '0'

    def _open_browser_when_ready(self, docs_url):
        for _ in range(40):
            try:
                with urlopen(docs_url, timeout=0.5):
                    webbrowser.open(docs_url)
                    return
            except (URLError, OSError):
                pass
            threading.Event().wait(0.25)
