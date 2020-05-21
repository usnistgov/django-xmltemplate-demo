from abc import ABC, abstractmethod


"""Module Python"""
class AbstractProductA(View, metaclass=ABCMeta):

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


"""
Concrete Products are created by corresponding Concrete Factories.
"""

"""Text_type_python"""
class ConcreteProductA1(AbstractProductA, metaclass=ABCMeta):
    """
    """

    def __init__(self, scripts=list(), styles=list(), config=None):
        """ Initialize module

        Args:
            scripts:
            styles:
        """
        scripts = ['xmltemplate/js/builtin/text_type.js'] + scripts
        AbstractProductA.__init__(self, scripts=scripts, styles=styles)
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
        else:
            html = 'default.html'
        return AbstractProductA.render_template(html, params)

    @abstractmethod
    def _get_date_content(self):
        """ Process data to build the type
        """
        raise NotImplementedError("not implemented")



class ConcreteProductA2(AbstractProductA, metaclass=ABCMeta):
    """Date_type_python"""

    def __init__(self, scripts=list(), styles=list(), config=None):
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
        else:
            html = 'default.html'
        return AbstractModule.render_template(html, params)

    @abstractmethod
    def _get_date_content(self):
        """ Process data to build the type
        """
        raise NotImplementedError("not implemented")


"""Module R"""
class AbstractProductB(metaclass=ABCMeta):
    """
    Here's the the base interface of another product. All products can interact
    with each other, but proper interaction is possible only between products of
    the same concrete variant.
    """

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
        raise NotImplementedError("_render_data method is not implemented.")

    def post(self, request):
        """
        Handle post requests
        :param request:
        :return:
        """

        raise NotImplementedError("_render_data method is not implemented.")

        @abstractmethod
        def get_resources(self):
            """Returns HTTP response containing module resources
            """
            raise NotImplementedError("_render_data method is not implemented.")

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
        raise NotImplementedError("_render_data method is not implemented.")

"""Text_type_python"""
class ConcreteProductB1(AbstractProductB, metaclass=ABCMeta):
    """Text_Type module
    """

    def __init__(self, scripts=list(), styles=list(), button_label='', config=None):
        """ Initialize module

        Args:
            scripts:
            styles:
        """
        scripts = ['xmltemplate/js/builtin/text_type.js'] + scripts
        AbstractProductA.__init__(self, scripts=scripts, styles=styles)
        self.config = config

    def _render_type(self, request, config, module):
        """ Return type's rendering

        Args:
            request:

        Returns:

        """
        params = {
            "text_content": self._get_text_content(),
        }
        if config == 'choice_1':
            html = 'xmltemplate/builtin/text_type_1.html'
        if not params:
            html = 'xmltemplate/builtin/date_type_2.html'

        return AbstractProductB.render_template(html, params)

    @abstractmethod
    def _get_text_content(self):
        """ Process data to build the type
        """
        raise NotImplementedError("not implemented")


"""Class_Type R"""
class ConcreteProductB2(AbstractProductB, metaclass=ABCMeta):
    """Popup module
    """

    def __init__(self, scripts=list(), styles=list(), button_label='', config=None):
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
            "text_content": self._get_text_content(),
        }
        if config == 'choice_1':
            html = 'xmltemplate/builtin/text_type_1.html'
        if not params:
            html = 'xmltemplate/builtin/date_type_2.html'

        return AbstractProductB.render_template(html, params)

    @abstractmethod
    def _get_text_content(self):
        """ Process data to build the type
        """
        raise NotImplementedError("not implemented")

class AbstractFactory(ABC):
    """
    The Abstract Factory interface declares a set of methods that return
    different abstract products. These products are called a family and are
    related by a high-level theme or concept. Products of one family are usually
    able to collaborate among themselves. A family of products may have several
    variants, but the products of one variant are incompatible with products of
    another.
    """
    @abstractmethod
    def create_product_a(self) -> AbstractProductA:
        pass

    @abstractmethod
    def create_product_b(self) -> AbstractProductB:
        pass


class ConcreteFactory1(AbstractFactory):
    """
    Concrete Factories produce a family of products that belong to a single
    variant. The factory guarantees that resulting products are compatible. Note
    that signatures of the Concrete Factory's methods return an abstract
    product, while inside the method a concrete product is instantiated.
    """

    def create_product_a(self) -> ConcreteProductA1:
        return ConcreteProductA1()

    def create_product_b(self) -> ConcreteProductB1:
        return ConcreteProductB1()


class ConcreteFactory2(AbstractFactory):
    """
    Each Concrete Factory has a corresponding product variant.
    """

    def create_product_a(self) -> ConcreteProductA2:
        return ConcreteProductA2()

    def create_product_b(self) -> ConcreteProductB2:
        return ConcreteProductB2()



"""
Concrete Products are created by corresponding Concrete Factories.
"""


def client_code(factory: AbstractFactory) -> None:
    """
    The client code works with factories and products only through abstract
    types: AbstractFactory and AbstractProduct. This lets you pass any factory
    or product subclass to the client code without breaking it.
    """
    product_a = factory.create_product_a()
    product_b = factory.create_product_b()

    print(f"{product_b.useful_function_b()}")
    print(f"{product_b.another_useful_function_b(product_a)}", end="")


if __name__ == "__main__":
    """
    The client code can work with any concrete factory class.
    """
    print("Client: Testing client code with the first factory type:")
    client_code(ConcreteFactory1())

    print("\n")

    print("Client: Testing the same client code with the second factory type:")
    client_code(ConcreteFactory2())


