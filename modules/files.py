import os
import json

class Files:
    cwd = os.getcwd()

    @classmethod
    def save_to_file(cls, file, data) -> None:
        with open(os.path.join(cls.cwd, file), 'w') as f:
            if (type(data) is str):
                f.write(data)
            else:
                f.write(json.dumps(data, indent=4))

    @classmethod
    def append_to_file(cls, file, data) -> None:
        with open(os.path.join(cls.cwd, file), 'a') as f:
            if (type(data) is str):
                f.write(data)
            else:
                f.write(json.dumps(data, indent=4))

    @classmethod
    def read_from_file(cls, file, return_type='json') -> str|dict:
        with open(os.path.join(cls.cwd, file), 'r') as f:
            if (return_type == 'json'):
                return json.loads(f.read().strip('\n'))
            else:
                return f.read().strip('\n')

