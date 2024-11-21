# coding: utf-8

"""
    Lambda Cloud API

    API for interacting with the Lambda GPU Cloud

    The version of the OpenAPI document: 1.5.3
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


import unittest

from openapi_client.models.add_ssh_key_request import AddSSHKeyRequest

class TestAddSSHKeyRequest(unittest.TestCase):
    """AddSSHKeyRequest unit test stubs"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def make_instance(self, include_optional) -> AddSSHKeyRequest:
        """Test AddSSHKeyRequest
            include_optional is a boolean, when False only required
            params are included, when True both required and
            optional params are included """
        # uncomment below to create an instance of `AddSSHKeyRequest`
        """
        model = AddSSHKeyRequest()
        if include_optional:
            return AddSSHKeyRequest(
                name = 'macbook-pro',
                public_key = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDfKpav4ILY54InZe27G user'
            )
        else:
            return AddSSHKeyRequest(
                name = 'macbook-pro',
        )
        """

    def testAddSSHKeyRequest(self):
        """Test AddSSHKeyRequest"""
        # inst_req_only = self.make_instance(include_optional=False)
        # inst_req_and_optional = self.make_instance(include_optional=True)

if __name__ == '__main__':
    unittest.main()
