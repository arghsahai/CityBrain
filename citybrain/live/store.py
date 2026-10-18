"""Bounded local prototype storage. No patient records or credentials."""
import json
import os
import sqlite3
import threading
from pathlib import Path


class Store:
    def __init__(self, path=':memory:'):
        if path != ':memory:':
            target = Path(path).expanduser()
            target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            # Refuse symlinks and constrain new/existing database permissions.
            fd = os.open(target,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            os.close(fd)
            os.chmod(target,0o600)
            path = str(target)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path,check_same_thread=False)
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, updated REAL, body TEXT, PRIMARY KEY(kind,id))')
        self.db.commit()

    def rows(self,kind):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute('SELECT body FROM records WHERE kind=? ORDER BY updated DESC,id',(kind,))]

    def get(self,kind,key):
        with self.lock:
            row = self.db.execute('SELECT body FROM records WHERE kind=? AND id=?',(kind,key)).fetchone()
            return json.loads(row[0]) if row else None

    def put(self,kind,key,value,now,limit=1000):
        with self.lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?,?)',(kind,key,now,json.dumps(value,allow_nan=False)))
            self.db.execute('DELETE FROM records WHERE kind=? AND id NOT IN (SELECT id FROM records WHERE kind=? ORDER BY updated DESC,rowid DESC LIMIT ?)',(kind,kind,limit))

    def prune(self,now):
        with self.lock,self.db:
            self.db.execute('DELETE FROM records WHERE updated < ?',(now-86400,))

    def delete(self,kind,key):
        with self.lock,self.db:
            self.db.execute('DELETE FROM records WHERE kind=? AND id=?',(kind,key))

    def close(self):
        self.db.close()
