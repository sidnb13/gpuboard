# coding: utf-8

"""
    Lambda Cloud API

    API for interacting with the Lambda GPU Cloud

    The version of the OpenAPI document: 1.5.3
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


import unittest

from openapi_client.models.restart_instance_request import RestartInstanceRequest

class TestRestartInstanceRequest(unittest.TestCase):
    """RestartInstanceRequest unit test stubs"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def make_instance(self, include_optional) -> RestartInstanceRequest:
        """Test RestartInstanceRequest
            include_optional is a boolean, when False only required
            params are included, when True both required and
            optional params are included """
        # uncomment below to create an instance of `RestartInstanceRequest`
        """
        model = RestartInstanceRequest()
        if include_optional:
            return RestartInstanceRequest(
                instance_ids = [
                    '0920582c7ff041399e34823a0be62549'
                    ]
            )
        else:
            return RestartInstanceRequest(
                instance_ids = [
                    '0920582c7ff041399e34823a0be62549'
                    ],
        )
        """

    def testRestartInstanceRequest(self):
        """Test RestartInstanceRequest"""
        # inst_req_only = self.make_instance(include_optional=False)
        # inst_req_and_optional = self.make_instance(include_optional=True)

if __name__ == '__main__':
    unittest.main()
