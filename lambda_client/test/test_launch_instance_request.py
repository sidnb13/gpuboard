# coding: utf-8

"""
    Lambda Cloud API

    API for interacting with the Lambda GPU Cloud

    The version of the OpenAPI document: 1.5.3
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


import unittest

from openapi_client.models.launch_instance_request import LaunchInstanceRequest

class TestLaunchInstanceRequest(unittest.TestCase):
    """LaunchInstanceRequest unit test stubs"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def make_instance(self, include_optional) -> LaunchInstanceRequest:
        """Test LaunchInstanceRequest
            include_optional is a boolean, when False only required
            params are included, when True both required and
            optional params are included """
        # uncomment below to create an instance of `LaunchInstanceRequest`
        """
        model = LaunchInstanceRequest()
        if include_optional:
            return LaunchInstanceRequest(
                region_name = 'us-tx-1',
                instance_type_name = 'gpu_1x_a100',
                ssh_key_names = [
                    'macbook-pro'
                    ],
                file_system_names = [
                    'shared-fs'
                    ],
                quantity = 1,
                name = 'training-node-1'
            )
        else:
            return LaunchInstanceRequest(
                region_name = 'us-tx-1',
                instance_type_name = 'gpu_1x_a100',
                ssh_key_names = [
                    'macbook-pro'
                    ],
        )
        """

    def testLaunchInstanceRequest(self):
        """Test LaunchInstanceRequest"""
        # inst_req_only = self.make_instance(include_optional=False)
        # inst_req_and_optional = self.make_instance(include_optional=True)

if __name__ == '__main__':
    unittest.main()
