#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import unittest

from pyspark.testing.connectutils import should_test_connect

if should_test_connect:
    from pyspark import sql
    from pyspark.sql.connect.udtf import UserDefinedTableFunction

    sql.udtf.UserDefinedTableFunction = UserDefinedTableFunction

from pyspark.sql.connect.functions import lit, udtf
from pyspark.sql.tests.test_udtf import BaseUDTFTestsMixin, UDTFArrowTestsMixin
from pyspark.testing.connectutils import ReusedConnectTestCase
from pyspark.errors.exceptions.connect import SparkConnectGrpcException


class UDTFParityTests(BaseUDTFTestsMixin, ReusedConnectTestCase):
    @classmethod
    def setUpClass(cls):
        super(UDTFParityTests, cls).setUpClass()
        cls.spark.conf.set("spark.sql.execution.pythonUDTF.arrow.enabled", "false")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.spark.conf.unset("spark.sql.execution.pythonUDTF.arrow.enabled")
        finally:
            super(UDTFParityTests, cls).tearDownClass()

    # TODO: use PySpark error classes instead of SparkConnectGrpcException

    def test_udtf_with_invalid_return_type(self):
        @udtf(returnType="int")
        class TestUDTF:
            def eval(self, a: int):
                yield a + 1,

        with self.assertRaisesRegex(
            SparkConnectGrpcException, "Invalid Python user-defined table function return type."
        ):
            TestUDTF(lit(1)).collect()

    def test_udtf_with_wrong_num_output(self):
        err_msg = (
            "java.lang.IllegalStateException: Input row doesn't have expected number of "
            + "values required by the schema."
        )

        @udtf(returnType="a: int, b: int")
        class TestUDTF:
            def eval(self, a: int):
                yield a,

        with self.assertRaisesRegex(SparkConnectGrpcException, err_msg):
            TestUDTF(lit(1)).collect()

        @udtf(returnType="a: int")
        class TestUDTF:
            def eval(self, a: int):
                yield a, a + 1

        with self.assertRaisesRegex(SparkConnectGrpcException, err_msg):
            TestUDTF(lit(1)).collect()

    def test_udtf_terminate_with_wrong_num_output(self):
        err_msg = (
            "java.lang.IllegalStateException: Input row doesn't have expected number of "
            "values required by the schema."
        )

        @udtf(returnType="a: int, b: int")
        class TestUDTF:
            def eval(self, a: int):
                yield a, a + 1

            def terminate(self):
                yield 1, 2, 3

        with self.assertRaisesRegex(SparkConnectGrpcException, err_msg):
            TestUDTF(lit(1)).show()

        @udtf(returnType="a: int, b: int")
        class TestUDTF:
            def eval(self, a: int):
                yield a, a + 1

            def terminate(self):
                yield 1,

        with self.assertRaisesRegex(SparkConnectGrpcException, err_msg):
            TestUDTF(lit(1)).show()

    @unittest.skip("Spark Connect does not support broadcast but the test depends on it.")
    def test_udtf_with_analyze_using_broadcast(self):
        super().test_udtf_with_analyze_using_broadcast()

    @unittest.skip("Spark Connect does not support accumulator but the test depends on it.")
    def test_udtf_with_analyze_using_accumulator(self):
        super().test_udtf_with_analyze_using_accumulator()

    def _add_pyfile(self, path):
        self.spark.addArtifacts(path, pyfile=True)

    def _add_archive(self, path):
        self.spark.addArtifacts(path, archive=True)

    def _add_file(self, path):
        self.spark.addArtifacts(path, file=True)


class ArrowUDTFParityTests(UDTFArrowTestsMixin, UDTFParityTests):
    @classmethod
    def setUpClass(cls):
        super(ArrowUDTFParityTests, cls).setUpClass()
        cls.spark.conf.set("spark.sql.execution.pythonUDTF.arrow.enabled", "true")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.spark.conf.unset("spark.sql.execution.pythonUDTF.arrow.enabled")
        finally:
            super(ArrowUDTFParityTests, cls).tearDownClass()


if __name__ == "__main__":
    import unittest
    from pyspark.sql.tests.connect.test_parity_udtf import *  # noqa: F401

    try:
        import xmlrunner  # type: ignore[import]

        testRunner = xmlrunner.XMLTestRunner(output="target/test-reports", verbosity=2)
    except ImportError:
        testRunner = None
    unittest.main(testRunner=testRunner, verbosity=2)
