"""Tests for Proposal forms."""
# pylint: disable=too-many-arguments

from funnel import models


def test_proposal_label_admin_form(
    forms,
    app,
    new_main_label,
    new_main_label_unrestricted,
    new_label,
    new_proposal,
) -> None:
    assert new_main_label.restricted
    assert not new_main_label_unrestricted.restricted
    assert not new_label.restricted
    assert not new_label.has_options

    with app.test_request_context():
        label_admin_form = forms.ProposalLabelsAdminForm(
            obj=new_proposal, model=models.Proposal, parent=new_proposal.project
        )
    # Label form in admin panel shows restricted and optioned labels
    assert hasattr(label_admin_form.formlabels, new_main_label.name)
    # Label form in admin panel doesn't show unrestricted labels
    assert not hasattr(label_admin_form.formlabels, new_main_label_unrestricted.name)
    # Label form in admin panel shows non-optioned labels
    assert hasattr(label_admin_form.formlabels, new_label.name)
    # test the field label text and id
    assert (
        getattr(label_admin_form.formlabels, new_label.name).label.text
        == new_label.form_label_text
    )

    assert (
        getattr(label_admin_form.formlabels, new_label.name).label.field_id
        == new_label.name
    )


def test_proposal_label_form(
    forms,
    app,
    new_main_label,
    new_main_label_unrestricted,
    new_label,
    new_proposal,
) -> None:
    assert new_main_label.restricted
    assert not new_main_label_unrestricted.restricted
    assert not new_label.restricted
    assert not new_label.has_options

    with app.test_request_context():
        label_form = forms.ProposalLabelsForm(
            obj=new_proposal, model=models.Proposal, parent=new_proposal.project
        )
    # Label form in edit page doesn't show restricted labels
    assert not hasattr(label_form.formlabels, new_main_label.name)
    # Label form in edit page shows non-restricted optioned labels
    assert hasattr(label_form.formlabels, new_main_label_unrestricted.name)
    # Label form in edit page doesn't show non-optioned labels
    assert not hasattr(label_form.formlabels, new_label.name)
