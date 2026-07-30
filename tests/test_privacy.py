from __future__ import annotations

import pandas as pd

from careerproof.privacy import contains_unmasked_pii, mask_dataframe, mask_email, mask_phone, mask_text


def test_email_is_masked():
    masked = mask_email("jordan.lee@example.com")
    assert masked.endswith("@example.com")
    assert "jordan.lee" not in masked
    assert "j*****" in masked


def test_phone_is_masked():
    masked = mask_phone("(206) 555-0123")
    assert masked == "***-***-0123"


def test_dataframe_masks_names_contacts_and_ids():
    frame = pd.DataFrame(
        {
            "recruiter_name": ["Jordan Lee"],
            "recruiter_email": ["jordan.lee@example.com"],
            "recruiter_phone": ["(206) 555-0123"],
            "source_record_id": ["SYN-20260730-12345"],
        }
    )
    text = mask_dataframe(frame).to_csv(index=False)
    assert "Jordan Lee" not in text
    assert "jordan.lee@example.com" not in text
    assert "(206) 555-0123" not in text
    assert "SYN-20260730-12345" not in text
    assert not contains_unmasked_pii(text)


def test_query_parameters_are_masked():
    masked = mask_text("https://example.com/path?token=secret&view=1")
    assert "secret" not in masked
    assert "token=%2A%2A%2A" in masked
