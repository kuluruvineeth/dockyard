import pytest

from app.validators import ValidationError, validate_url_domain, validate_url_path


class TestDomainValidators:
    def test_validate_url_domain_succesfull(self):
        validate_url_domain("dky.local")

    def test_validate_url_domain_succesfull_for_subdomains(self):
        validate_url_domain("git.dky.local")

    def test_validate_url_domain_without_http(self):
        with pytest.raises(ValidationError):
            validate_url_domain("http://dky.local")

    def test_validate_url_domain_without_pathname(self):
        with pytest.raises(ValidationError):
            validate_url_domain("dky.local/hello")

    def test_validate_url_domain_without_search_params(self):
        with pytest.raises(ValidationError):
            validate_url_domain("dky.local?hello=world")

    def test_validate_url_domain_without_hashtag(self):
        with pytest.raises(ValidationError):
            validate_url_domain("dky.local#hello=world")

    def test_validate_url_wildcard_subdomain(self):
        validate_url_domain("*.gh.dockyard.dev")

    def test_validate_url_wildcard_double_subdomain(self):
        with pytest.raises(ValidationError):
            validate_url_domain("*.*.gh.dockyard.dev")


class TestBasePathValidators:
    def test_validate_base_path_succesfull(self):
        validate_url_path("/hello")

    def test_validate_base_path_succesfull_for_multi_path(self):
        validate_url_path("/hello/world")

    def test_validate_base_path_succesfull_for_slash(self):
        validate_url_path("/")

    def test_validate_base_path_without_domain(self):
        with pytest.raises(ValidationError):
            validate_url_path("google.com/")

    def test_validate_base_path_without_double_dots(self):
        with pytest.raises(ValidationError):
            validate_url_path("../")

    def test_validate_base_path_with_dots(self):
        validate_url_path("/hello.world")

    def test_validate_base_path_without_star(self):
        with pytest.raises(ValidationError):
            validate_url_path("/hello/*")

    def test_validate_base_path_without_slash(self):
        with pytest.raises(ValidationError):
            validate_url_path("hello/*")
