class AbstractModule(View, metaclass=ABCMeta):

    def __init__(self, scripts=list(), styles=list(), data=None, config=None, moduleid=None):
        """Initializes the type

        :param scripts    list:    list of javascript scripts
        :param styles    list:    list of css files
        """

        # JS scripts
        self.scripts = scripts
        # CSS spreadsheets
        self.styles = styles

        # initialize data
        self.data = data

        # initialize configuration data
        self.config = config
        self.module = moduleid
    def _get(self, request):
        """ Manage the GET requests

        Args:
            request:

        Returns:

        """
        module_id = ''
        type_id = request.GET['type_id']
        try:
            module_id = request.GET['module_id']
        except Exception as e:
            pass
        url = request.GET['url']
        config = request.GET['config']
        template_data = {
            'config':config,
            'type_id': type_id,
            'type': '',
            'module_id': module_id,
            'module': '',
            'display': '',
            'url': url
        }

        try:

            self.data = self._retrieve_data
            # get module's rendering
            if module_id != '':
                template_data['module'] = get_module_by_id(template_data['module_id'])
                template_data['module_id'] = template_data['module']._render_module(request)
            else:
                template_data['type'] = self._render_type(request, template_data['config'])
            # get module's data rendering
            template_data['display'] = self._render_data(request,template_data['config'])
        except Exception as e:
            pass
        # Check that values are not None
        for key, val in list(template_data.items()):
            if val is None:
                raise ValueError

        # Apply tags to the template
        html_string = TypeRendererSpec.render_template(self.template_name, template_data)
        return HttpResponse(html_string, status=HTTP_200_OK)

    def post(self, request):
        """
        Handle post requests
        :param request:
        :return:
        """

        template_data = {
            'display': '',
            'url': ''
        }
        try:
            if 'template_id' not in request.POST:
                return HttpResponseBadRequest({'error': 'No "type_id" parameter provided'})

            type_element = data_structure_element_api.get_by_id(request.POST['type_id'])
            # retrieve the type data

            self.data = self._retrieve_data(request)
            template_data['display'] = self._render_data(request)
            options = type_element.options

            if type(self.data) == dict:
                options['data'] = self.data['data']
                options['attributes'] = self.data['attributes']
            else:
                options['data'] = self.data

            # TODO Implement this system instead
            # options['content'] = self._get_content(request)
            # options['attributes'] = self._get_attributes(request)

            type_element.options = options
            data_structure_element_api.upsert(type_element)
        except Exception as e:
            raise ModuleError('Something went wrong during module update: ' + str(e))

        html_code = AbstractType.render_template(self.template_name, template_data)

        response_dict = dict()
        response_dict['html'] = html_code

        if hasattr(self, "get_XpathAccessor"):
            response_dict.update(self.get_XpathAccessor())

            return HttpResponse(json.dumps(response_dict))

        @abstractmethod
        def get_resources(self):
            """Returns HTTP response containing module resources
            """
            response = {
                'scripts': self.scripts,
                'styles': self.styles
            }

            return HttpResponse(json.dumps(response), status=HTTP_200_OK)

        @abstractmethod
        def _retrieve_data(self, request):
            """ Retrieve module's data

            Args:
                request:

            Returns:

            """
            raise NotImplementedError("_retrieve_data method is not implemented.")

        @abstractmethod
        def _render_data(self, request):
            """ Re  turn the module's data representation

            Args:
                request:

            Returns:

            """
            raise NotImplementedError("_render_data method is not implemented.")

       @staticmethod
        def render_template(template_name, context=None):
            """ Renders the module in HTML using django template

            Args:
                template_name:
                context:

            Returns:

            """
            if context is None:
                context = {}

            template = get_template(template_name)
            return template.render(context)
