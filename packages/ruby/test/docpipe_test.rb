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

  def test_document_exposes_coordinates_and_provenance
    coordinates = { "backend" => "pymupdf", "origin" => "top-left", "units" => "pt" }
    cell = { "text" => "Qty", "page" => 1, "bbox" => [200.0, 100.0, 300.0, 120.0] }
    doc = Docpipe::Document.new(
      "markdown" => "",
      "text" => "",
      "pages" => [{ "number" => 1, "elements" => [{ "type" => "table", "rows" => [[cell]] }] }],
      "metadata" => {},
      "backend" => "pymupdf",
      "coordinates" => coordinates
    )

    assert_equal coordinates, doc.coordinates
    assert_equal [200.0, 100.0, 300.0, 120.0], doc.pages.first["elements"].first["rows"].first.first["bbox"]
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
