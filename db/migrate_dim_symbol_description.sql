ALTER TABLE staging.dim_symbol
    ADD COLUMN IF NOT EXISTS description TEXT;

UPDATE staging.dim_symbol
SET
    description = CASE symbol_code
        WHEN 'VCB' THEN 'A leading state-owned bank with strong asset quality and profitability. It dominates trade finance and foreign exchange, and is widely seen as one of the safest banks in Vietnam.'
        WHEN 'CTG' THEN 'A large state-owned commercial bank with a strong corporate lending base. It plays a key role in financing industrial and infrastructure sectors, though margins are relatively tighter.'
        WHEN 'BID' THEN 'The largest bank by assets in Vietnam, with extensive exposure to government and infrastructure projects. Growth is stable but often comes with higher provisioning pressure.'
        WHEN 'TCB' THEN 'A top-tier private bank known for high profitability and strong capital efficiency. It focuses on retail and real estate ecosystems, with advanced digital banking capabilities.'
        WHEN 'VPB' THEN 'A high-growth private bank driven by consumer finance and SME lending. It offers strong yield but also carries higher credit risk compared to peers.'
        WHEN 'MBB' THEN 'A military-linked bank with strong operational efficiency and asset quality. It has a diversified ecosystem including insurance, securities, and digital banking platforms.'
        WHEN 'ACB' THEN 'A retail-focused private bank with conservative risk management. It delivers stable growth and is known for consistent profitability and clean balance sheet.'
        WHEN 'STB' THEN 'A bank in the late stage of restructuring after past issues. It offers turnaround potential as asset quality improves and legacy problems are gradually resolved.'
        WHEN 'SHB' THEN 'A mid-sized bank with strong corporate lending exposure. It is expanding retail banking, though asset quality remains a key factor to watch.'
        WHEN 'HDB' THEN 'A fast-growing bank with strong ties to consumer finance and aviation (VietJet ecosystem). It benefits from retail expansion and high-margin lending segments.'
        WHEN 'VIB' THEN 'A retail-oriented bank specializing in auto loans and digital banking. It maintains strong profitability with a focus on individual customers.'
        WHEN 'TPB' THEN 'A digital-first bank backed by major shareholders. It stands out for innovation in online banking and rapid growth in retail customers.'
        WHEN 'OCB' THEN 'A mid-tier bank focusing on SMEs and retail clients. It is undergoing digital transformation to improve efficiency and competitiveness.'
        WHEN 'MSB' THEN 'A commercial bank transitioning toward retail and SME segments. It shows improving asset quality and profitability in recent years.'
        WHEN 'LPB' THEN 'A unique bank leveraging Vietnam''s postal network for nationwide reach. It focuses on financial inclusion, especially in rural areas.'
        WHEN 'SSB' THEN 'A growing private bank with strong backing from foreign investors. It is expanding retail banking while improving operational efficiency.'
        WHEN 'EIB' THEN 'Traditionally strong in import-export financing. The bank is restructuring to stabilize governance and improve long-term performance.'
        WHEN 'BAB' THEN 'A niche bank focused on agriculture and sustainable projects. It has a unique lending strategy tied to specific industries.'
        WHEN 'NVB' THEN 'A small-scale bank serving retail and SME customers. Growth potential exists but scale and efficiency remain limited.'
        WHEN 'PGB' THEN 'A small bank with origins in the petroleum sector. It is undergoing strategic changes to improve scale and competitiveness.'
        WHEN 'SGB' THEN 'One of the oldest joint-stock banks in Vietnam. It maintains a traditional retail banking model with moderate growth.'
        WHEN 'NAB' THEN 'A rising private bank focusing on digital transformation and retail expansion. It aims to improve efficiency and market share.'
        WHEN 'FPT' THEN 'Leading Vietnamese technology group with strong growth in software exports, digital transformation, telecom, and education segments.'
        WHEN 'VIC' THEN 'Vietnam''s largest private conglomerate with diversified exposure to real estate, hospitality, and industrial ventures including EV manufacturing.'
        WHEN 'VNM' THEN 'Vietnam''s dominant dairy producer with strong brand equity, stable cash flow, and extensive domestic and export distribution networks.'
        WHEN 'HPG' THEN 'Leading steel producer in Vietnam with integrated production model, benefiting from scale advantages and industrial expansion.'
        WHEN 'MWG' THEN 'Top retail group operating electronics, appliance, and grocery chains, with strong execution capability and nationwide store network.'
        WHEN 'VHM' THEN 'Largest residential real estate developer in Vietnam, focusing on large-scale urban projects with strong sales pipeline and brand recognition.'
        ELSE description
    END,
    updated_at = CURRENT_TIMESTAMP
WHERE symbol_code IN (
    'VCB', 'CTG', 'BID', 'TCB', 'VPB', 'MBB', 'ACB', 'STB', 'SHB', 'HDB',
    'VIB', 'TPB', 'OCB', 'MSB', 'LPB', 'SSB', 'EIB', 'BAB', 'NVB', 'PGB',
    'SGB', 'NAB', 'FPT', 'VIC', 'VNM', 'HPG', 'MWG', 'VHM'
)
AND (description IS NULL OR description = '');
