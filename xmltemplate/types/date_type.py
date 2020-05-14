""" Text rendmod
"""
from abc import ABCMeta, abstractmethod

from xmltemplate.module import AbstractModule


class DateModule(AbstractModule, metaclass=ABCMeta):
    """Popup module
    """

    def __init__(self, scripts=list(), styles=list(), config = None):
        """ Initialize module

        Args:
            scripts:
            styles:
        """
        scripts = ['xmltemplate/js/builtin/text_type.js'] + scripts
        AbstractModule.__init__(self, scripts=scripts, styles=styles)
        self.config = config

    def _render_type(self, request, config, module):
        """ Return type's rendering

        Args:
            request:

        Returns:

        """
        params = {
            "date_content": self._get_date_content(),
        }
        if config == 'choice_1':
            html = 'xmltemplate/builtin/date_type_1.html'
        elif config == 'choice_2':
            html = 'xmltemplate/builtin/date_type_2.html'
        else :
            html = 'default.html'
        return AbstractModule.render_template(html, params)

    @abstractmethod
    def _get_date_content(self):
        """ Process data to build the type
        """
        raise NotImplementedError("not implemented")
