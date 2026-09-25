module Docpipe
  class Document
    attr_reader :data

    def initialize(data)
      @data = data
    end

    def markdown
      data.fetch("markdown")
    end

    def text
      data.fetch("text")
    end

    def pages
      data.fetch("pages")
    end

    def metadata
      data.fetch("metadata")
    end

    def backend
      data.fetch("backend")
    end
  end
end
