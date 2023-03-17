import json

from typing import Dict
from pathlib import Path

class Utils():
    class FileUtil():
        @classmethod
        def read_by_guild(cls, path: Path, guild_id: int) -> Dict:
            return cls._read(path, filename=str(guild_id))
    
        @classmethod
        def save_by_guild(cls, data:Dict, guild_id: int, path: Path) -> Dict:
            return cls._save(data=data, path=path, filename=str(guild_id))

        @classmethod
        def _read(cls, path: Path, filename = "data") -> Dict:
            file = path / Path(filename + ".json")
            try:
                with open(file, encoding='utf-8',mode='r') as f:
                    return json.load(f)
            except FileNotFoundError:
                print(file.name,"が見つかりません。作成します。")
            except json.JSONDecodeError:
                print(file.name,"が不正です。上書きします。")
            cls._save(data={}, path=path, filename=filename)
            return {}

        @classmethod
        def _save(cls, data: Dict, path: Path, filename = "data") -> None:
            file = path / Path(filename + ".json")
            if not path.exists() or not file.exists():
                path.mkdir(parents=True, exist_ok=True)
                file.touch(exist_ok=True)
            with open(file, encoding='utf-8',mode='w') as f:
                json.dump(data, f, indent=2)