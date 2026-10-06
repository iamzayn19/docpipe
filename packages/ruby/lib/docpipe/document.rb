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

    # Coordinate contract for bounding boxes ([x0, y0, x1, y1]); nil when no backend produced boxes.
    def coordinates
      data["coordinates"]
    end
  end
end
