import datetime
import os
import sqlite3
import time
import unittest

import kodistubs
from clouddrive.common.cache.cache import Cache
from clouddrive.common.db import SimpleKeyValueDb

ACCOUNT = {'id': 'a1', 'name': 'Carlos Guzmán', 'drives': [{'id': 'd1', 'shared': True, 'name': None}],
           'access_tokens': {'access_token': 'AT', 'refresh_token': 'RT', 'expires_in': 3600, 'date': 1760000000.5}}


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.path = kodistubs.use_temp_profile()

    def raw(self, db, table='store'):
        return sqlite3.connect(os.path.join(self.path, db)).execute('select value from %s' % table).fetchall()

    def test_values_round_trip_as_json(self):
        db = SimpleKeyValueDb(self.path, 'accounts')
        db.set('a1', ACCOUNT)
        self.assertEqual(db.get('a1'), ACCOUNT)
        self.assertEqual(db.getall(), {'a1': ACCOUNT})
        self.assertTrue(self.raw('accounts.db')[0][0].startswith('json:{'))

    def test_rows_of_earlier_versions_are_read(self):
        con = sqlite3.connect(os.path.join(self.path, 'accounts.db'))
        con.execute('create table store(key text unique, value text)')
        con.execute('insert into store values (?, ?)', ('a1', repr(ACCOUNT)))
        con.commit()
        self.assertEqual(SimpleKeyValueDb(self.path, 'accounts').get('a1'), ACCOUNT)

    def test_stored_code_is_never_run(self):
        con = sqlite3.connect(os.path.join(self.path, 'accounts.db'))
        con.execute('create table store(key text unique, value text)')
        con.execute('insert into store values (?, ?)', ('x', "__import__('os').getcwd()"))
        con.commit()
        with self.assertRaises(ValueError):
            SimpleKeyValueDb(self.path, 'accounts').get('x')

    def test_query_errors_are_logged_not_raised(self):
        db = SimpleKeyValueDb(self.path, 'accounts')
        self.assertIsNone(db._execute_sql('select * from missing_table'))

    def test_locked_database_is_retried(self):
        db = SimpleKeyValueDb(self.path, 'accounts')
        db.set('a', 1)
        locker = sqlite3.connect(os.path.join(self.path, 'accounts.db'), isolation_level=None, check_same_thread=False)
        locker.execute('begin exclusive')
        attempts = []
        real_connect = sqlite3.connect

        def connect(*args, **kwargs):
            kwargs['timeout'] = 0.01
            return real_connect(*args, **kwargs)

        def wait(seconds):
            attempts.append(seconds)
            if len(attempts) == 2:
                locker.execute('commit')
        db._monitor.waitForAbort = wait
        with unittest.mock.patch('sqlite3.connect', side_effect=connect):
            db.set('b', {'x': 1})
        self.assertEqual(len(attempts), 2)
        self.assertEqual(db.get('b'), {'x': 1})

    def test_shutdown_stops_the_retries(self):
        db = SimpleKeyValueDb(self.path, 'accounts')
        db.set('a', 1)
        locker = sqlite3.connect(os.path.join(self.path, 'accounts.db'), isolation_level=None, check_same_thread=False)
        locker.execute('begin exclusive')
        attempts = []
        real_connect = sqlite3.connect

        def connect(*args, **kwargs):
            kwargs['timeout'] = 0.01
            return real_connect(*args, **kwargs)

        def wait(seconds):
            attempts.append(seconds)
            return True  # Kodi asked to stop.
        db._monitor.waitForAbort = wait
        try:
            with unittest.mock.patch('sqlite3.connect', side_effect=connect):
                self.assertIsNone(db._execute_sql("insert or replace into store(key, value) values('b', 'x')"))
            self.assertEqual(len(attempts), 1)
        finally:
            locker.execute('commit')

    def test_cache_expires_and_purges_on_write(self):
        # A controlled clock: the cache keeps whole seconds, so real sleeps made this test flaky.
        import clouddrive.common.cache.cache as cache_module
        clock = [datetime.datetime(2026, 10, 16, 12, 0, 0, 999000)]
        fake = unittest.mock.MagicMock(timedelta=datetime.timedelta)
        fake.datetime.now.side_effect = lambda: clock[0]
        patcher = unittest.mock.patch.object(cache_module, 'datetime', fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        cache = Cache('addon', 'items', datetime.timedelta(seconds=1))
        cache.setmany([['k1', {'n': 1}], ['k2', ['a']]])
        clock[0] += datetime.timedelta(milliseconds=2)
        self.assertEqual(cache.get('k1'), {'n': 1}, 'still valid just after a whole second ticks over')
        clock[0] += datetime.timedelta(seconds=2)
        self.assertIsNone(cache.get('k1'))
        cache.set('k3', 'v')
        self.assertEqual([r[0] for r in sqlite3.connect(os.path.join(self.path, 'cache_items.db')).execute('select key from cache')], ['k3'])
        cache.clear()
        self.assertIsNone(cache.get('k3'))


if __name__ == '__main__':
    unittest.main()
