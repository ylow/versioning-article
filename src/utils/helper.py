import os
import pathlib
import shutil
import subprocess
from loguru import logger
import pyxet
import duckdb
import os.path as path


class Helper:
    def __init__(self):
        origins = subprocess.run('git remote -v', shell=True, cwd='xethub', stdout=subprocess.PIPE).stdout.decode()
        origin = origins.split('\n')[0].split('\t')[1].split(' ')[0].split('/')
        self.fs = pyxet.XetFS()
        self.xet_repo = f"xet://{origin[-2]}/{origin[-1].replace('.git','')}/main"

    @staticmethod
    def copy_file(filepath: str, repo: str):
        filename = os.path.basename(filepath)
        targetpath = os.path.join(repo, filename)
        shutil.copyfile(filepath, targetpath)
        return filename

    def dvc_push(self, repo):
        command = """
                  dvc push
                  """
        return self.run(command, repo)

    def git_push(self, repo):
        command = """
                  git push
                  """
        self.run(command, repo)

    def run(self, command, repo):
        logger.debug(command)
        logger.debug(subprocess.run(command, capture_output=True, shell=True, cwd=repo))

    def dvc_upload(self, filepath: str):
        filename = os.path.basename(filepath)
        command = f"""
                        dvc add {filename}
                        git add {filename}.dvc
                        git commit -m "commit {filename}"
                        git push                
                        """
        self.run(command, 'dvc')
        self.dvc_push('dvc')

    def git_add_commit(self, filename: str, repo: str):
        command = f"""                                
                    git add {filename}
                    git commit -m "commit {filename}"
                    """
        self.run(command, repo)

    def _git_upload(self, filepath: str, repo: str):
        filename = os.path.basename(filepath)
        self.git_add_commit(filename, repo)
        self.git_push(repo)

    def lfs_upload(self, filepath: str):
        self._git_upload(filepath, 'lfs')

    def xethub_upload(self, filepath: str, pyxet_api: bool = True):
        filename = os.path.basename(filepath)
        if pyxet_api:
            with self.fs.transaction:
                self.fs.put(filepath, f"{self.xet_repo}/{filename}")
        else:
            if filename not in pathlib.Path('xethub').glob('*'):
                self.copy_file(filepath, f"xethub/{filename}")
            self._git_upload(filepath, 'xethub')

    def output_upload(self, output: str = 'output.csv'):
        self.git_add_commit(output, None)
        self.git_push(None)

    def merge_files(self, new_filepath: str, merged_filepath: str):
        if not path.exists(merged_filepath):
            shutil.copyfile(new_filepath, merged_filepath)
        else:
            duckdb.execute(f"""
                        COPY (SELECT * FROM read_parquet(['{new_filepath}', '{merged_filepath}'])) TO '{merged_filepath}' (FORMAT 'parquet');
                        """)
        return merged_filepath

    def xet_ls(self):
        return self.fs.ls(self.xet_repo, detail=False)

    def xet_remove(self, filename: str):
        with self.fs.transaction:
            self.fs.rm(f"{self.xet_repo}/{filename}")