#!/usr/bin/env ruby

# 脚本在 integrations/anystyle/，submodule 在 third_party/anystyle/
SCRIPT_DIR = File.dirname(__FILE__)
ROOT_DIR = File.expand_path('../../third_party/anystyle', SCRIPT_DIR)
LIB_DIR = File.join(ROOT_DIR, 'lib')

# set LOAD_PATH
$LOAD_PATH.delete_if { |p| p.include?('anystyle') }
$LOAD_PATH.unshift(LIB_DIR)

require 'anystyle'

# read from stdin
input = STDIN.read
exit if input.nil? || input.strip.empty?

# 解析
dataset = AnyStyle.parse(input, format: :wapiti)

# 输出 JSON
require 'json'
puts JSON.pretty_generate(AnyStyle.parser.format_csl(dataset))