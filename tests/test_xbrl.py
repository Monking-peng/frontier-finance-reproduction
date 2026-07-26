from decimal import Decimal

from ffrepro.xbrl import InlineXbrlDocument


def test_extracts_dimensioned_usd_fact_in_millions() -> None:
    source = """
    <xbrli:context id="c-1">
      <xbrli:entity><xbrli:segment>
        <xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">
          tsla:AutomotiveSalesMember
        </xbrldi:explicitMember>
      </xbrli:segment></xbrli:entity>
      <xbrli:period>
        <xbrli:startDate>2024-01-01</xbrli:startDate>
        <xbrli:endDate>2024-12-31</xbrli:endDate>
      </xbrli:period>
    </xbrli:context>
    <ix:nonFraction unitRef="usd" contextRef="c-1" decimals="-6"
      name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
      scale="6">72,480</ix:nonFraction>
    """
    document = InlineXbrlDocument.from_text(source)
    value = document.usd_millions(
        concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        start_date="2024-01-01",
        end_date="2024-12-31",
        member_suffix="AutomotiveSalesMember",
    )
    assert value == Decimal("72480")


def test_rejects_dimensioned_fact_for_consolidated_lookup() -> None:
    source = """
    <xbrli:context id="c-1">
      <xbrli:entity><xbrli:segment>
        <xbrldi:explicitMember dimension="axis">tsla:AutomotiveSalesMember</xbrldi:explicitMember>
      </xbrli:segment></xbrli:entity>
      <xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>
      <xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period>
    </xbrli:context>
    <ix:nonFraction unitRef="usd" contextRef="c-1"
      name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
      scale="6">72,480</ix:nonFraction>
    """
    document = InlineXbrlDocument.from_text(source)
    try:
        document.usd_millions(
            concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            start_date="2024-01-01",
            end_date="2024-12-31",
            member_suffix=None,
        )
    except LookupError:
        pass
    else:
        raise AssertionError("dimensioned fact must not satisfy a consolidated lookup")
