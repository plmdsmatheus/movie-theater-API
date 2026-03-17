from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """
    I centralize the default pagination behavior for all list endpoints.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100