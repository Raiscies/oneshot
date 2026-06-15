#!/usr/bin/env ruby

require 'anystyle'

# read from stdin
input = STDIN.read
exit if input.nil? || input.strip.empty?

# 解析
dataset = AnyStyle.parse(input, format: :wapiti)

# 输出 JSON
require 'json'
puts JSON.pretty_generate(AnyStyle.parser.format_csl(dataset))