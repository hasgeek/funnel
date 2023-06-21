"""Notification helpers and mixins."""

from ...models import Project


class ProjectTemplateMixin:
    """Mixin class for SMS templates mentioning a project."""

    var_max_length: int
    project: Project

    @property
    def project_title(self) -> str:
        """Return project joined title or title, truncated to fit the length limit."""
        if len(self.project.joined_title) <= self.var_max_length:
            return self.project.joined_title
        if len(self.project.title) <= self.var_max_length:
            return self.project.title
        return self.project.title[: self.var_max_length - 1] + '…'
