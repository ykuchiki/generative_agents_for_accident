import json
import numpy
import datetime
import random
import os
import sys

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.global_methods import *
from backend.utils import *
from backend.persona.prompt_template.gpt_structure import *

##############################################################################
#                    PERSONA Chapter 1: Prompt Structures                    #
##############################################################################

def print_run_prompts(prompt_template=None,
                      persona=None,
                      gpt_param=None,
                      prompt_input=None,
                      prompt=None,
                      output=None):
  print (f"=== {prompt_template}")
  print ("~~~ persona    ---------------------------------------------------")
  print (persona.name, "\n")
  print ("~~~ gpt_param ----------------------------------------------------")
  print (gpt_param, "\n")
  print ("~~~ prompt_input    ----------------------------------------------")
  print (prompt_input, "\n")
  print ("~~~ prompt    ----------------------------------------------------")
  print (prompt, "\n")
  print ("~~~ output    ----------------------------------------------------")
  print (output, "\n")
  print ("=== END ==========================================================")
  print ("\n\n\n")

