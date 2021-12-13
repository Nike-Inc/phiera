import pytest
from phiera import Merge
import unittest

deep_merge_testset = (
    (
        {"list": [-1, 8, 1, 2, 3, 4, 5, 6]},
        {"list": [6, 7, 4, 3, 8, 11, 2, 13, 12, 3]},
        {"list": [-1, 8, 1, 2, 3, 4, 5, 6, 7, 11, 13, 12]}
    ),
    (
        {"list": [-1, 8, 1, 2, 3, 4, 5, 6]},
        {"list": 100000},
        {"list": [-1, 8, 1, 2, 3, 4, 5, 6, 100000]}
    ),
)

deep_merge_testset_dict = (
    (
        {"dict": {'a': 'b', 'c': 'd'}},
        {"dict": {'a': {'b': 'c'}}},
        {"dict": {'a': {'b': 'c'}, 'c': 'd'}}
    ),
    (
        {"dict": {'a': 1, 'b': 2, 'c': {'d': 3}}},
        {"dict": {'e': 5}},
        {"dict": {'a': 1, 'b': 2, 'c': {'d': 3}, 'e': 5}}
    ),
)

deep_merge_testset_set = (
    (
        {"set": {1, 2, 3}},
        {"set": {1, 2, 3, 4, 5}},
        {"set": {1, 2, 3, 4, 5}}
    ),
    (
        {"set": {3, 2, 1, 0}},
        {"set": {1, 2, 3}},
        {"set": {1, 2, 3}}
    )
)


@pytest.mark.parametrize("arg1, arg2, expected", deep_merge_testset)
def test_deep_merge(arg1, arg2, expected):
    merge = Merge(list, deep=True)
    deep_merge_actual = merge.deep_merge(arg1, arg2)
    assert merge.deep_merge(arg1, arg2) == expected
    assert isinstance(deep_merge_actual['list'], list)


@pytest.mark.parametrize("arg1, arg2, expected", deep_merge_testset_dict)
def test_deep_merge_dict(arg1, arg2, expected):
    merge = Merge(dict, deep=True)
    deep_merge_actual = merge.deep_merge(arg1, arg2)
    assert merge.deep_merge(arg1, arg2) == expected
    assert isinstance(deep_merge_actual['dict'], dict)


@pytest.mark.parametrize("arg1, arg2, expected", deep_merge_testset_set)
def test_deep_merge_dict(arg1, arg2, expected):
    merge = Merge(set, deep=True)
    deep_merge_actual = merge.deep_merge(arg1, arg2)
    assert merge.deep_merge(arg1, arg2) == expected
    assert isinstance(deep_merge_actual['set'], set)


class BaseTestMergeValue(unittest.TestCase):

    def test_merge_value_list(self):
        merge = Merge(list)
        merge.merge_value({'list': ['a', 'b']})
        self.assertEqual(merge.typ, list)
        self.assertEqual(merge.deep, False)

    def test_merge_value_set(self):
        merge = Merge(set)
        merge.merge_value({-1, 8, 1, 2, 3, 4, 5, 6})
        self.assertEqual(merge.typ, set)
        self.assertEqual(merge.deep, False)

    def test_merge_value_str(self):
        merge = Merge(str)
        merge.merge_value('test_string')
        assert hasattr(merge.value, '__class__')
        self.assertEqual(merge.value, 'test_string')
        self.assertEqual(merge.typ, str)
        self.assertEqual(merge.deep, False)

    def test_merge_value_dict(self):
        merge = Merge(dict)
        merge.merge_value({'dict': {'a': 'b'}})
        assert hasattr(merge.value, '__dict__')
        self.assertEqual(merge.typ, dict)
        self.assertEqual(merge.deep, False)

    def test_merge_value_dict_deep(self):
        merge = Merge(dict, deep=True)
        merge.merge_value({'dict': {'a': 'b'}})
        assert hasattr(merge.value, '__dict__')
        self.assertEqual(merge.deep, True)

    def test_merge_value_raise(self):
        """
        Should raise TypeError when type not in (dict, list, set, string)
        """
        merge = Merge(tuple)
        with self.assertRaisesRegex(Exception, "Cannot handle merge_value of type %s".format(type(tuple))):
            merge.merge_value((-1, 8))
