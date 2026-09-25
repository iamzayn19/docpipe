require "minitest/autorun"
require "docpipe"
require "tmpdir"

class DocpipeTest < Minitest::Test
  def test_document_wrapper
    doc = Docpipe::Document.new(
      "markdown" => "Hello",
      "text" => "Hello",
      "pages" => [],
      "metadata" => {},
      "backend" => "test"
    )

    assert_equal "Hello", doc.markdown
    assert_equal "test", doc.backend
  end

  def test_python_executable_override
    Dir.mktmpdir("docpipe-ruby-") do |dir|
      python = File.join(dir, "python")
      File.write(
        python,
        <<~SH
          #!/bin/sh
          if [ "$5" = "markdown" ]; then
            printf 'Hello markdown'
          else
            printf '{"text":"Hello json","markdown":"Hello json","pages":[{"number":1,"tables":[]}]}'
          fi
        SH
      )
      File.chmod(0o755, python)

      original = ENV["DOCPIPE_PYTHON"]
      ENV["DOCPIPE_PYTHON"] = python
      assert_equal "Hello json", Docpipe.parse("sample.pdf").text
      assert_equal "Hello markdown", Docpipe.parse_markdown("sample.pdf")
    ensure
      ENV["DOCPIPE_PYTHON"] = original
    end
  end
end
