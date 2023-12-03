import tempfile
import unittest

import sweep
from . import db as db


class _DummyParam:
    def __init__(self, full_name: str, v: int):
        self.full_name = full_name
        self._v = v

    def __call__(self, sp=None):
        if sp is None:
            return self._v


class TestStation(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.dir.cleanup()

    def test_measure(self):
        s = sweep.Station(basedir=self.dir.name, verbose=True)
        s.fp(_DummyParam('p2', 1.0)).fp(_DummyParam('p3', 2.0))
        res = s.measure()
        with db.Reader(res.basedir, res.id) as r:
            self.assertEqual(r.metadata['type'], '0D')
            self.assertEqual(r.metadata['columns'][0], 'time')
            self.assertEqual(r.metadata['columns'][1], 'p2')
            self.assertEqual(len(r.all_data()), 1)
            self.assertEqual(float(r.all_data()[0][1]), 1.0)

    def test_sweep(self):
        s = sweep.Station(basedir=self.dir.name, verbose=True)
        s.fp(_DummyParam('p2', 1.0)).fp(_DummyParam('p3', 2.0))
        res = s.sweep(_DummyParam('p1', None), range(1000))
        with db.Reader(res.basedir, res.id) as r:
            self.assertEqual(r.metadata['type'], '1D')
            self.assertEqual(r.metadata['param'], 'p1')
            self.assertEqual(r.metadata['columns'][0], 'time')
            self.assertEqual(r.metadata['columns'][1], 'p1')
            self.assertEqual(r.metadata['columns'][2], 'p2')
            self.assertEqual(r.metadata['columns'][3], 'p3')
            self.assertEqual(len(r.all_data()), 1000)

    def test_sweep_plot(self):
        s = sweep.Station(basedir=self.dir.name, verbose=True)
        s.fp(_DummyParam('p2', 1.0)).fp(_DummyParam('p3', 2.0))
        s.plot('p1', 'p2')
        res = s.sweep(_DummyParam('p1', None), range(10))
        with db.Reader(res.basedir, res.id) as r:
            self.assertEqual(len(r.all_data()), 10)
            self.assertTrue(len(r.blob('plot.png')) > 0)


if __name__ == '__main__':
    unittest.main()
