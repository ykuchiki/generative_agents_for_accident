import random
import string
import csv
import time
import datetime as dt
import pathlib
import os
import sys
import numpy
import math
import shutil, errno

from os import listdir


def read_file_to_list(curr_file, header=False, strip_trail=True):
    """
    CSVファイルをリストのリストとして読み込む
    :param curr_file: 読み込むCSVファイルのパス
    :param header: ヘッダー行を含むか
    :param strip_trail: 各セルの前後の空白を取り除くかどうか
    :return: 各行がリストになっているリスト，またはヘッダーとデータ行のタプル
    """
    if not header:
        analysis_list = []
        with open(curr_file, 'r') as f:
            data_reader = csv.reader(f, delimiter=',')
            for count, row in enumerate(data_reader):
                if strip_trail:
                    row = [i.strip() for i in row]
                analysis_list += [row]
        return analysis_list
    else:
        analysis_list = []
        with open(curr_file, 'r') as f:
            data_reader = csv.reader(f, delimiter=',')
            for count, row in enumerate(data_reader):
                if strip_trail:
                    row = [i.strip() for i in row]
                analysis_list += [row]
        return analysis_list

def check_if_file_exists(curr_file):
    """
    ファイルが存在するか確認
    :param curr_file: 読み込むCSVファイルのパス
    :return: 存在するならTrue, しないならFalse
    """
    try:
        with open(curr_file, 'r') as f_analysis_file: pass  # パスのファイルが開けるかどうかだけ確認
        return True
    except:
        return False

def copyanything(src, dst):
  """
  Copy over everything in the src folder to dst folder.
  ARGS:
    src: address of the source folder
    dst: address of the destination folder
  RETURNS:
    None
  """
  src = os.path.abspath(src)
  dst = os.path.abspath(dst)
  if not os.path.exists(src):
      raise FileNotFoundError(f"Source path does not exist: {src}")
  try:
      shutil.copytree(src, dst)
  except OSError as e:
      if e.errno == shutil.errno.ENOTDIR:
          shutil.copy(src, dst)
      else:
          raise

def find_filenames(path_to_dir, suffix=".csv"):
  """
  Given a directory, find all files that ends with the provided suffix and
  returns their paths.
  ARGS:
    path_to_dir: Path to the current directory
    suffix: The target suffix.
  RETURNS:
    A list of paths to all files in the directory.
  """
  filenames = listdir(path_to_dir)
  return [ path_to_dir+"/"+filename
           for filename in filenames if filename.endswith( suffix ) ]

def create_folder_if_not_there(curr_path):
  """
  Checks if a folder in the curr_path exists. If it does not exist, creates
  the folder.
  Note that if the curr_path designates a file location, it will operate on
  the folder that contains the file. But the function also works even if the
  path designates to just a folder.
  Args:
    curr_list: list to write. The list comes in the following form:
               [['key1', 'val1-1', 'val1-2'...],
                ['key2', 'val2-1', 'val2-2'...],]
    outfile: name of the csv file to write
  RETURNS:
    True: if a new folder is created
    False: if a new folder is not created
  """
  outfolder_name = curr_path.split("/")
  if len(outfolder_name) != 1:
    # This checks if the curr path is a file or a folder.
    if "." in outfolder_name[-1]:
      outfolder_name = outfolder_name[:-1]

    outfolder_name = "/".join(outfolder_name)
    if not os.path.exists(outfolder_name):
      os.makedirs(outfolder_name)
      return True

  return False


if __name__ == '__main__':
    fork_folder = "frontend/storage/base_the_ville_isabella_maria_klaus"
    sim_folder = "frontend/storage/test-simulation"

    print(f"Source folder: {os.path.abspath(fork_folder)}")
    print(f"Destination folder: {os.path.abspath(sim_folder)}")



