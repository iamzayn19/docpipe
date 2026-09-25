require "minitest/autorun"
require "docpipe"

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
end
