require "json"
require "open3"
require_relative "docpipe/document"

module Docpipe
  class Error < StandardError; end

  def self.parse(path, ocr: "auto")
    python = ENV.fetch("DOCPIPE_PYTHON", "python3")
    stdout, stderr, status = Open3.capture3(
      python, "-m", "docpipe_core.cli", path.to_s, "--format", "json", "--ocr", ocr.to_s
    )
    raise Error, stderr.strip unless status.success?

    Document.new(JSON.parse(stdout))
  end

  def self.parse_markdown(path, ocr: "auto")
    python = ENV.fetch("DOCPIPE_PYTHON", "python3")
    stdout, stderr, status = Open3.capture3(
      python, "-m", "docpipe_core.cli", path.to_s, "--format", "markdown", "--ocr", ocr.to_s
    )
    raise Error, stderr.strip unless status.success?

    stdout
  end
end
