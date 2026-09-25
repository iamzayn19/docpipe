Gem::Specification.new do |spec|
  spec.name = "docpipe"
  spec.version = "0.1.0"
  spec.summary = "Document parsing to Markdown and JSON from Ruby."
  spec.description = "Ruby wrapper for Docpipe, a local-first document parser."
  spec.authors = ["Zayn"]
  spec.license = "MIT"
  spec.homepage = "https://github.com/iamzayn19/docpipe"
  spec.metadata = {
    "source_code_uri" => "https://github.com/iamzayn19/docpipe",
    "bug_tracker_uri" => "https://github.com/iamzayn19/docpipe/issues"
  }
  spec.required_ruby_version = ">= 3.0"
  spec.files = Dir["lib/**/*.rb", "README.md", "LICENSE"]
  spec.require_paths = ["lib"]
end
