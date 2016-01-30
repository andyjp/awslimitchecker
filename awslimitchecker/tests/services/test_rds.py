"""
awslimitchecker/tests/services/test_rds.py

The latest version of this package is available at:
<https://github.com/jantman/awslimitchecker>

################################################################################
Copyright 2015 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of awslimitchecker, also known as awslimitchecker.

    awslimitchecker is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    awslimitchecker is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with awslimitchecker.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/pydnstest> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""

import sys
import result_fixtures
from boto.rds2.layer1 import RDSConnection
from boto.rds2 import connect_to_region
from awslimitchecker.services.rds import _RDSService

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch, call, Mock, DEFAULT
else:
    from unittest.mock import patch, call, Mock, DEFAULT


class Test_RDSService(object):

    pb = 'awslimitchecker.services.rds._RDSService'  # patch base path
    pbm = 'awslimitchecker.services.rds'  # patch base path - module

    def test_init(self):
        """test __init__()"""
        cls = _RDSService(21, 43)
        assert cls.service_name == 'RDS'
        assert cls.conn is None
        assert cls.warning_threshold == 21
        assert cls.critical_threshold == 43

    def test_connect(self):
        """test connect()"""
        mock_conn = Mock()
        mock_conn_via = Mock()
        cls = _RDSService(21, 43)
        with patch('%s.boto.connect_rds2' % self.pbm) as mock_rds:
            with patch('%s.connect_via' % self.pb) as mock_connect_via:
                mock_rds.return_value = mock_conn
                mock_connect_via.return_value = mock_conn_via
                cls.connect()
        assert mock_rds.mock_calls == [call()]
        assert mock_conn.mock_calls == []
        assert mock_connect_via.mock_calls == []
        assert cls.conn == mock_conn

    def test_connect_region(self):
        """test connect()"""
        mock_conn = Mock()
        mock_conn_via = Mock()
        cls = _RDSService(21, 43, region='foo')
        with patch('%s.boto.connect_rds2' % self.pbm) as mock_rds:
            with patch('%s.connect_via' % self.pb) as mock_connect_via:
                mock_rds.return_value = mock_conn
                mock_connect_via.return_value = mock_conn_via
                cls.connect()
        assert mock_rds.mock_calls == []
        assert mock_conn.mock_calls == []
        assert mock_connect_via.mock_calls == [
            call(connect_to_region)
        ]
        assert cls.conn == mock_conn_via

    def test_connect_again(self):
        """make sure we re-use the connection"""
        mock_conn = Mock()
        cls = _RDSService(21, 43)
        cls.conn = mock_conn
        with patch('awslimitchecker.services.rds.boto.connect_rds2'
                   '') as mock_rds:
            with patch('%s.connect_via' % self.pb) as mock_connect_via:
                mock_rds.return_value = mock_conn
                cls.connect()
        assert mock_rds.mock_calls == []
        assert mock_conn.mock_calls == []
        assert mock_connect_via.mock_calls == []

    def test_get_limits(self):
        cls = _RDSService(21, 43)
        cls.limits = {}
        res = cls.get_limits()
        assert sorted(res.keys()) == sorted([
            # TA  # non-TA / service doc name
            'DB instances',  # 'Instances'
            'Max auths per security group',
            'Storage quota (GB)',  # 'Total storage for all DB instances'
            'DB snapshots per user',  # 'Manual Snapshots'
            'DB security groups',  # 'Security Groups'
            # non-TA
            'Reserved Instances',
            'DB parameter groups',
            'VPC Security Groups',
            'Subnet Groups',
            'Subnets per Subnet Group',
            'Option Groups',
            'Event Subscriptions',
            'Read replicas per master',
        ])
        for name, limit in res.items():
            assert limit.service == cls
            assert limit.def_warning_threshold == 21
            assert limit.def_critical_threshold == 43

    def test_get_limits_again(self):
        """test that existing limits dict is returned on subsequent calls"""
        mock_limits = Mock()
        cls = _RDSService(21, 43)
        cls.limits = mock_limits
        res = cls.get_limits()
        assert res == mock_limits

    def test_find_usage(self):
        mock_conn = Mock(spec_set=RDSConnection)

        with patch('%s.connect' % self.pb) as mock_connect:
            with patch.multiple(
                    self.pb,
                    _find_usage_instances=DEFAULT,
                    _find_usage_snapshots=DEFAULT,
                    _find_usage_param_groups=DEFAULT,
                    _find_usage_subnet_groups=DEFAULT,
                    _find_usage_option_groups=DEFAULT,
                    _find_usage_event_subscriptions=DEFAULT,
                    _find_usage_security_groups=DEFAULT,
                    _find_usage_reserved_instances=DEFAULT,
            ) as mocks:
                cls = _RDSService(21, 43)
                cls.conn = mock_conn
                assert cls._have_usage is False
                cls.find_usage()
        assert mock_connect.mock_calls == [call()]
        assert cls._have_usage is True
        for x in [
                '_find_usage_instances',
                '_find_usage_snapshots',
        ]:
            assert mocks[x].mock_calls == [call()]

    def test_required_iam_permissions(self):
        cls = _RDSService(21, 43)
        assert cls.required_iam_permissions() == [
            "rds:DescribeDBInstances",
            "rds:DescribeDBParameterGroups",
            "rds:DescribeDBSecurityGroups",
            "rds:DescribeDBSnapshots",
            "rds:DescribeDBSubnetGroups",
            "rds:DescribeEventSubscriptions",
            "rds:DescribeOptionGroups",
            "rds:DescribeReservedDBInstances",
        ]

    def test_find_usage_instances(self):
        mock_conn = Mock(spec_set=RDSConnection)
        cls = _RDSService(21, 43)
        cls.conn = mock_conn
        instances = result_fixtures.RDS.test_find_usage_instances
        return_value = {
            'DescribeDBInstancesResponse': {
                'DescribeDBInstancesResult': {
                    'DBInstances': instances
                }
            }
        }

        with patch('%s.boto_query_wrapper' % self.pbm) as mock_wrapper:
            mock_wrapper.return_value = return_value
            cls._find_usage_instances()

        assert mock_conn.mock_calls == []
        assert mock_wrapper.mock_calls == [
            call(
                mock_conn.describe_db_instances,
                alc_marker_path=[
                    'DescribeDBInstancesResponse',
                    'DescribeDBInstancesResult',
                    'Marker'
                ],
                alc_data_path=[
                    'DescribeDBInstancesResponse',
                    'DescribeDBInstancesResult',
                    'DBInstances'
                ],
                alc_marker_param='marker'
            )
        ]

        usage = sorted(cls.limits['DB instances'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 2
        assert usage[0].aws_type == 'AWS::RDS::DBInstance'

        usage = sorted(cls.limits['Storage quota (GB)'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 250
        assert usage[0].aws_type == 'AWS::RDS::DBInstance'

        usage = sorted(
            cls.limits['Read replicas per master'].get_current_usage()
        )
        assert len(usage) == 2
        assert usage[0].get_value() == 0
        assert usage[0].resource_id == 'foo'
        assert usage[1].get_value() == 2
        assert usage[1].resource_id == 'baz'

    def test_find_usage_snapshots(self):
        data = result_fixtures.RDS.test_find_usage_snapshots

        mock_conn = Mock(spec_set=RDSConnection)
        cls = _RDSService(21, 43)
        cls.conn = mock_conn

        with patch('%s.boto_query_wrapper' % self.pbm) as mock_wrapper:
            mock_wrapper.return_value = data
            cls._find_usage_snapshots()

        assert mock_conn.mock_calls == []
        assert mock_wrapper.mock_calls == [
            call(
                mock_conn.describe_db_snapshots,
                alc_marker_path=[
                    "DescribeDBSnapshotsResponse",
                    "DescribeDBSnapshotsResult",
                    'Marker'
                ],
                alc_data_path=[
                    "DescribeDBSnapshotsResponse",
                    "DescribeDBSnapshotsResult",
                    "DBSnapshots"
                ],
                alc_marker_param='marker'
            )
        ]

        usage = sorted(cls.limits['DB snapshots per user'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 1
        assert usage[0].aws_type == 'AWS::RDS::DBSnapshot'

    def test_find_usage_param_groups(self):
        data = result_fixtures.RDS.test_find_usage_param_groups

        mock_conn = Mock(spec_set=RDSConnection)
        cls = _RDSService(21, 43)
        cls.conn = mock_conn

        with patch('%s.boto_query_wrapper' % self.pbm) as mock_wrapper:
            mock_wrapper.return_value = data
            cls._find_usage_param_groups()

        assert mock_conn.mock_calls == []
        assert mock_wrapper.mock_calls == [
            call(
                mock_conn.describe_db_parameter_groups,
                alc_marker_path=[
                    "DescribeDBParameterGroupsResponse",
                    "DescribeDBParameterGroupsResult",
                    'Marker'
                ],
                alc_data_path=[
                    "DescribeDBParameterGroupsResponse",
                    "DescribeDBParameterGroupsResult",
                    "DBParameterGroups"
                ],
                alc_marker_param='marker'
            )
        ]

        usage = sorted(cls.limits['DB parameter groups'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 2
        assert usage[0].aws_type == 'AWS::RDS::DBParameterGroup'

    def test_find_usage_subnet_groups(self):
        data = result_fixtures.RDS.test_find_usage_subnet_groups

        mock_conn = Mock(spec_set=RDSConnection)
        cls = _RDSService(21, 43)
        cls.conn = mock_conn

        with patch('%s.boto_query_wrapper' % self.pbm) as mock_wrapper:
            mock_wrapper.return_value = data
            cls._find_usage_subnet_groups()

        assert mock_conn.mock_calls == []
        assert mock_wrapper.mock_calls == [
            call(
                mock_conn.describe_db_subnet_groups,
                alc_marker_path=[
                    "DescribeDBSubnetGroupsResponse",
                    "DescribeDBSubnetGroupsResult",
                    "Marker"
                ],
                alc_data_path=[
                    "DescribeDBSubnetGroupsResponse",
                    "DescribeDBSubnetGroupsResult",
                    "DBSubnetGroups"
                ],
                alc_marker_param='marker'
            )
        ]

        usage = sorted(cls.limits['Subnet Groups'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 3
        assert usage[0].aws_type == 'AWS::RDS::DBSubnetGroup'
        usage = sorted(
            cls.limits['Subnets per Subnet Group'].get_current_usage()
        )
        assert len(usage) == 3
        assert usage[0].get_value() == 1
        assert usage[0].aws_type == 'AWS::RDS::DBSubnetGroup'
        assert usage[0].resource_id == "SubnetGroup2"
        assert usage[1].get_value() == 2
        assert usage[1].aws_type == 'AWS::RDS::DBSubnetGroup'
        assert usage[1].resource_id == "SubnetGroup1"
        assert usage[2].get_value() == 3
        assert usage[2].aws_type == 'AWS::RDS::DBSubnetGroup'
        assert usage[2].resource_id == "default"

    def test_find_usage_option_groups(self):
        data = result_fixtures.RDS.test_find_usage_option_groups

        mock_conn = Mock(spec_set=RDSConnection)
        cls = _RDSService(21, 43)
        cls.conn = mock_conn

        with patch('%s.boto_query_wrapper' % self.pbm) as mock_wrapper:
            mock_wrapper.return_value = data
            cls._find_usage_option_groups()

        assert mock_conn.mock_calls == []
        assert mock_wrapper.mock_calls == [
            call(
                mock_conn.describe_option_groups,
                alc_marker_path=[
                    "DescribeOptionGroupsResponse",
                    "DescribeOptionGroupsResult",
                    "Marker"
                ],
                alc_data_path=[
                    "DescribeOptionGroupsResponse",
                    "DescribeOptionGroupsResult",
                    "OptionGroupsList"
                ],
                alc_marker_param='marker'
            )
        ]

        usage = sorted(cls.limits['Option Groups'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 2
        assert usage[0].aws_type == 'AWS::RDS::DBOptionGroup'

    def test_find_usage_event_subscriptions(self):
        data = result_fixtures.RDS.test_find_usage_event_subscriptions

        mock_conn = Mock(spec_set=RDSConnection)
        cls = _RDSService(21, 43)
        cls.conn = mock_conn

        with patch('%s.boto_query_wrapper' % self.pbm) as mock_wrapper:
            mock_wrapper.return_value = data
            cls._find_usage_event_subscriptions()

        assert mock_conn.mock_calls == []
        assert mock_wrapper.mock_calls == [
            call(
                mock_conn.describe_event_subscriptions,
                alc_marker_path=[
                    "DescribeEventSubscriptionsResponse",
                    "DescribeEventSubscriptionsResult",
                    "Marker"
                ],
                alc_data_path=[
                    "DescribeEventSubscriptionsResponse",
                    "DescribeEventSubscriptionsResult",
                    "EventSubscriptionsList"
                ],
                alc_marker_param='marker'
            )
        ]

        usage = sorted(cls.limits['Event Subscriptions'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 1
        assert usage[0].aws_type == 'AWS::RDS::EventSubscription'

    def test_find_usage_security_groups(self):
        data = result_fixtures.RDS.test_find_usage_security_groups

        mock_conn = Mock(spec_set=RDSConnection)
        cls = _RDSService(21, 43)
        cls.conn = mock_conn

        with patch('%s.boto_query_wrapper' % self.pbm) as mock_wrapper:
            mock_wrapper.return_value = data
            cls._find_usage_security_groups()

        assert mock_conn.mock_calls == []
        assert mock_wrapper.mock_calls == [
            call(
                mock_conn.describe_db_security_groups,
                alc_marker_path=[
                    "DescribeDBSecurityGroupsResponse",
                    "DescribeDBSecurityGroupsResult",
                    "Marker"
                ],
                alc_data_path=[
                    "DescribeDBSecurityGroupsResponse",
                    "DescribeDBSecurityGroupsResult",
                    "DBSecurityGroups"
                ],
                alc_marker_param='marker'
            )
        ]

        usage = sorted(cls.limits['DB security groups'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 2
        assert usage[0].aws_type == 'AWS::RDS::DBSecurityGroup'

        usage = sorted(cls.limits['VPC Security Groups'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 2
        assert usage[0].aws_type == 'AWS::RDS::DBSecurityGroup'

        usage = sorted(cls.limits[
                           'Max auths per security group'].get_current_usage())
        assert len(usage) == 4
        assert usage[0].get_value() == 0
        assert usage[0].resource_id == 'default:vpc-a926c2cc'
        assert usage[0].aws_type == 'AWS::RDS::DBSecurityGroup'
        assert usage[1].get_value() == 1
        assert usage[1].resource_id == 'SecurityGroup1'
        assert usage[1].aws_type == 'AWS::RDS::DBSecurityGroup'
        assert usage[2].get_value() == 2
        assert usage[2].resource_id == 'alctest'
        assert usage[2].aws_type == 'AWS::RDS::DBSecurityGroup'
        assert usage[3].get_value() == 3
        assert usage[3].resource_id == 'SecurityGroup2'
        assert usage[3].aws_type == 'AWS::RDS::DBSecurityGroup'

    def test_find_usage_reserved_instances(self):
        data = result_fixtures.RDS.test_find_usage_reserved_instances

        mock_conn = Mock(spec_set=RDSConnection)
        cls = _RDSService(21, 43)
        cls.conn = mock_conn

        with patch('%s.boto_query_wrapper' % self.pbm) as mock_wrapper:
            mock_wrapper.return_value = data
            cls._find_usage_reserved_instances()

        assert mock_conn.mock_calls == []
        assert mock_wrapper.mock_calls == [
            call(
                mock_conn.describe_reserved_db_instances,
                alc_marker_path=[
                    'DescribeReservedDBInstancesResponse',
                    'DescribeReservedDBInstancesResult',
                    "Marker"
                ],
                alc_data_path=[
                    'DescribeReservedDBInstancesResponse',
                    'DescribeReservedDBInstancesResult',
                    'ReservedDBInstances'
                ],
                alc_marker_param='marker'
            )
        ]

        usage = sorted(cls.limits['Reserved Instances'].get_current_usage())
        assert len(usage) == 1
        assert usage[0].get_value() == 2
        assert usage[0].aws_type == 'AWS::RDS::DBInstance'
