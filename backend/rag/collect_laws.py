"""
Wakeel وکیل — Pakistani Law Data Collector
Run ONCE to build your law database:
    python rag/collect_laws.py
"""

import os, re, time, requests
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw_laws"
RAW_DIR.mkdir(exist_ok=True)

CORE_LAW_DATA = {

"ppc_core.txt": """PAKISTAN PENAL CODE 1860 — CORE SECTIONS

SECTION 302 — MURDER (Qatl-i-Amd)
Whoever commits Qatl-i-Amd shall be punished with death as Qisas, or imprisonment for life.
NON-BAILABLE. COGNIZABLE. Maximum: Death. Accused must be produced before magistrate within 24 hours.
Right to counsel guaranteed under Article 10A Constitution. Bail rarely granted.

SECTION 307 — ATTEMPT TO COMMIT MURDER
Punished with imprisonment up to ten years and Diyat. NON-BAILABLE.

SECTION 324 — ATTEMPT TO CAUSE HURT
Imprisonment up to three years or fine or both. NON-BAILABLE.

SECTION 354 — ASSAULT ON WOMAN
Whoever assaults or uses criminal force to any woman intending to outrage her modesty shall be
punished with imprisonment which may extend to two years, or with fine, or with both.
NON-BAILABLE. COGNIZABLE. Police can arrest without warrant.

SECTION 376 — RAPE (Zina-Bil-Jabr)
Punished with death or imprisonment not less than ten years nor more than twenty-five years and fine.
NON-BAILABLE. Victim rights: female doctor examination, identity protection, in-camera trial.

SECTION 392 — ROBBERY
Rigorous imprisonment up to ten years and fine. NON-BAILABLE.

SECTION 395 — DACOITY (Gang Robbery — 5 or more persons)
Imprisonment for life or rigorous imprisonment up to ten years and fine. NON-BAILABLE.

SECTION 406 — CRIMINAL BREACH OF TRUST
Imprisonment up to three years or fine or both. NON-BAILABLE.

SECTION 420 — CHEATING AND FRAUD
Whoever cheats and dishonestly induces delivery of property shall be punished with imprisonment
up to seven years and fine. NON-BAILABLE. Common in commercial disputes.

SECTION 447 — CRIMINAL TRESPASS
Imprisonment up to three months or fine up to Rs.500 or both. BAILABLE.

SECTION 489-F — DISHONOURED CHEQUE
Imprisonment up to three years or fine or both. BAILABLE. Most common financial offence.
Accused must prove arrangements were made with bank to honour cheque.

SECTION 506 — CRIMINAL INTIMIDATION
Part 1 (threat): imprisonment up to two years or fine. BAILABLE.
Part 2 (death threat): imprisonment up to seven years. NON-BAILABLE.

SECTION 109 — ABETMENT
Same punishment as the principal offence abetted.

SECTION 34 — COMMON INTENTION (Joint Liability)
When criminal act done by several persons in furtherance of common intention,
each person is liable as if he alone committed the act.

SECTION 295-C — BLASPHEMY (Derogatory remarks re Prophet PBUH)
Punished with death or imprisonment for life and fine. NON-BAILABLE. Mandatory death sentence.

SECTION 499 — DEFAMATION
Making or publishing imputation to harm reputation. BAILABLE. NOT COGNIZABLE.

SECTION 379/380 — THEFT / THEFT IN DWELLING
Theft in dwelling house: imprisonment up to seven years and fine. NON-BAILABLE.
""",

"constitution_core.txt": """CONSTITUTION OF PAKISTAN 1973 — FUNDAMENTAL RIGHTS

ARTICLE 9 — SECURITY OF PERSON
No person shall be deprived of life or liberty save in accordance with law.
Remedy for violation: Habeas Corpus petition under Article 199 in High Court.

ARTICLE 10 — SAFEGUARDS ON ARREST
Every arrested person must be produced before a magistrate within 24 hours.
Must be informed of grounds of arrest immediately.
Cannot be compelled to be witness against himself.

ARTICLE 10A — RIGHT TO FAIR TRIAL
Every person is entitled to fair trial and due process.
Guarantees: impartial tribunal, right to be heard, right to legal counsel.

ARTICLE 13 — PROTECTION AGAINST DOUBLE PUNISHMENT
No person shall be prosecuted for same offence more than once (double jeopardy).
No person shall be compelled to be witness against himself (self-incrimination).
Confessions obtained through torture are inadmissible in court.

ARTICLE 14 — DIGNITY OF MAN
Dignity of man is inviolable. Privacy of home is inviolable.
No person shall be subjected to torture to extract evidence.
Police torture violates Article 14. FIR can be filed against police officers.

ARTICLE 25 — EQUALITY OF CITIZENS
All citizens are equal before law and entitled to equal protection of law.
No discrimination on basis of sex, religion, caste, or race.

ARTICLE 199 — HIGH COURT JURISDICTION (Constitutional Petitions)
High Court can issue writs:
- Habeas Corpus: produce unlawfully detained person
- Mandamus: compel performance of public duty
- Certiorari: quash illegal orders of inferior courts
File petition under Article 199 when fundamental rights are violated.

ARTICLE 184(3) — SUPREME COURT JURISDICTION
Any citizen can file Human Rights Case directly in Supreme Court.
For matters of public importance involving fundamental rights.
Supreme Court can take suo motu action on fundamental rights violations.
""",

"crpc_core.txt": """CODE OF CRIMINAL PROCEDURE 1898 — KEY SECTIONS

SECTION 54 — ARREST WITHOUT WARRANT
Police may arrest without warrant for cognizable offences only.
Non-cognizable offences require magistrate's warrant.

SECTION 61 — 24-HOUR RULE
No arrested person shall be detained beyond 24 hours without magistrate authority.
This is a fundamental right under Article 10 Constitution.

SECTION 167 — POLICE REMAND
Magistrate may authorize detention for investigation up to 15 days total.
After 15 days without challan: accused must be released on bail.

SECTION 173 — CHALLAN (Charge Sheet)
Police must file charge sheet (challan) in court after investigation.
If no challan filed within prescribed time, accused entitled to bail.

SECTION 22-A — JUSTICE OF PEACE
If police refuse to register FIR, apply to Justice of Peace (Executive Magistrate).
Justice of Peace can direct police to register FIR.
This is a crucial remedy when police refuse to act.

SECTION 496 — BAIL IN BAILABLE OFFENCES
In bailable offences, bail is a RIGHT. Police and courts MUST grant bail.
Cannot be refused without specific legal reason.

SECTION 497 — BAIL IN NON-BAILABLE OFFENCES
In non-bailable offences, bail is at court's DISCRETION.
For capital offences (death/life imprisonment): bail is very difficult to obtain.
Court considers: flight risk, evidence tampering risk, criminal history.

SECTION 498 — PRE-ARREST BAIL (Anticipatory Bail)
Apply to Sessions Court or High Court BEFORE arrest.
File when you fear false FIR or arrest.
Court may grant protective bail pending investigation.

SECTION 374 — DEATH SENTENCE CONFIRMATION
All death sentences must be confirmed by High Court before execution.
Defendant has right to appeal to Supreme Court.
""",

"bail_guide.txt": """BAIL IN PAKISTAN — COMPLETE GUIDE

BAILABLE OFFENCES:
Bail is a LEGAL RIGHT. Police must grant bail when accused offers surety.
Examples: Criminal trespass (447 PPC), dishonoured cheque (489-F), defamation (499).
If police refuse: File complaint with SP or approach magistrate directly.

NON-BAILABLE OFFENCES:
Bail is at COURT'S DISCRETION.
Apply to magistrate (for offences up to 3 years) or sessions court (serious offences).
High Court can grant bail in any case.
Murder (302), robbery (392), rape (376) are non-bailable.

PRE-ARREST BAIL (ANTICIPATORY BAIL):
Apply BEFORE being arrested when you fear false FIR.
File application in Sessions Court or High Court.
Show: FIR is mala fide, you are cooperating, no flight risk.

BAIL APPLICATION PROCEDURE:
1. Hire a lawyer immediately after arrest.
2. Lawyer files bail application with FIR copy.
3. Court hears prosecution and defence.
4. If granted, accused provides surety (financial guarantee).
5. Surety amount set by court based on offence severity.

GROUNDS FOR BAIL REFUSAL:
- Accused likely to flee jurisdiction
- Risk of tampering with evidence
- Risk of intimidating witnesses
- Gravity of offence
- Prior criminal record

APPEAL AGAINST BAIL REFUSAL:
Magistrate Court → Sessions Court → High Court → Supreme Court.
Each higher court can grant bail even if lower court refused.

YOUR RIGHTS AFTER ARREST:
1. Right to know grounds of arrest immediately.
2. Right to be produced before magistrate within 24 hours.
3. Right to contact family and lawyer.
4. Right to remain silent (no self-incrimination).
5. Right against torture — Article 14 Constitution.
6. Right to bail in bailable offences.
7. Right to free legal aid if cannot afford lawyer.
""",

"family_law.txt": """FAMILY LAW IN PAKISTAN

NIKAH (MARRIAGE):
Nikah Nama must be registered with Union Council. Failure to register: fine.
For valid nikah: offer and acceptance, witnesses, dower (mehr).
Minimum age: 16 for girls, 18 for boys (Child Marriage Restraint Act).

TALAQ (DIVORCE BY HUSBAND):
Under Muslim Family Laws Ordinance 1961:
1. Husband pronounces talaq in any form.
2. Must send written notice to Union Council Chairman within required period.
3. Copy of notice must be given to wife.
4. Talaq effective after 90 days from notice to Union Council.
5. During 90 days: reconciliation is possible.
If husband does NOT send notice to Union Council: talaq still pronounced but husband
can face imprisonment up to 1 year or fine Rs.5000 or both.

KHUL (DIVORCE BY WIFE):
Wife can seek dissolution of marriage by:
1. Khul: wife returns dower to husband, husband agrees to release.
2. Judicial dissolution (Faskh): file case in Family Court under Dissolution of
   Muslim Marriages Act 1939. Grounds include: 4 years disappearance, 2 years
   failure to maintain, imprisonment 7+ years, cruelty, impotency.
3. Mubarat: mutual agreement to dissolve marriage.

MEHR (DOWER):
Prompt mehr (Mahr-i-Muajjal): payable on demand immediately.
Deferred mehr (Mahr-i-Muwajjal): payable on divorce or death of husband.
Wife can sue for unpaid mehr in Family Court.

MAINTENANCE (NAFAQAH):
Husband obligated to maintain wife during marriage and during iddat after divorce.
Wife can apply to Union Council or Family Court for maintenance order.
Children's maintenance is father's responsibility until sons are 18 and daughters married.

CUSTODY OF CHILDREN:
Mother has right to custody (hizanat) of:
- Sons up to age 7
- Daughters up to puberty
After these ages, father gets custody unless court decides otherwise in child's interest.
Family Court has jurisdiction over all custody disputes.

INHERITANCE:
Son gets double share of daughter.
Daughter gets half of son's share.
Spouse inherits from deceased spouse.
Grandchildren inherit per stirpes if parent predeceases grandparent.
Illegitimate children do not inherit from father under Muslim law.

FAMILY COURT JURISDICTION:
All family matters (divorce, maintenance, custody, dower, inheritance disputes)
go to Family Court exclusively, not sessions court or civil court.
File application in Family Court of the area where you or husband resides.
""",

"labour_law.txt": """LABOUR LAWS IN PAKISTAN

TERMINATION OF EMPLOYMENT:
After 3 months continuous service: 1 month notice required or 1 month pay in lieu.
Unfair dismissal: File complaint in Labour Court within 30 days.
Wrongful termination compensation: Up to 24 months wages.

GRATUITY:
After completing 1 year continuous service: 30 days wages per year of service.
Gratuity is mandatory. Employer cannot refuse to pay.
File complaint in Labour Court if employer refuses.

WORKING HOURS:
Maximum 9 hours per day, 48 hours per week (Factories Act 1934).
Overtime: Double the ordinary wage rate.
Right to 1 rest day per week.
Annual leave: 14 days after 12 months service.

EOBI (OLD-AGE BENEFITS):
Compulsory for all establishments with 5+ employees.
Provides old-age pension, invalidity pension, survivors pension.
If employer not registered: file complaint with EOBI office.

MINIMUM WAGE:
Punjab/Sindh 2024: Rs.32,000 per month.
KPK 2024: Rs.28,000 per month.
Paying below minimum wage: employer liable to prosecution.

MATERNITY LEAVE:
Under Maternity Benefit Ordinance 1958: 12 weeks paid maternity leave.
Cannot be dismissed during maternity leave.

WORKPLACE HARASSMENT:
Protection Against Harassment of Women at Workplace Act 2010.
Every employer must constitute an Inquiry Committee.
Complaint to committee → if unsatisfied → Federal/Provincial Ombudsman.
Fine up to Rs.500,000 for employers failing to comply.

LABOUR COURT:
File complaints about: unfair dismissal, unpaid wages, illegal deductions,
failure to pay gratuity or EOBI.
Labour Court in every district. Filing is free for workers.
""",

"rent_laws.txt": """RENT LAWS IN PAKISTAN

TENANT RIGHTS:
1. Cannot be evicted without Rent Controller or court order.
2. Landlord cannot forcibly lock out tenant — this is a criminal offence.
3. Security deposit must be returned within reasonable time after vacating.
4. Rent increases limited to 10% per year in Punjab (Punjab Rented Premises Act 2009).
5. If landlord cuts utilities (water, electricity) to force eviction: criminal complaint possible.

GROUNDS FOR LEGAL EVICTION (Punjab Rented Premises Act 2009):
(a) 2 months default in rent payment
(b) Subletting premises without permission
(c) Using premises for illegal purpose
(d) Causing substantial damage to premises
(e) Landlord genuinely requires premises for personal use
(f) Major reconstruction/repairs required

EVICTION PROCEDURE:
Landlord must file ejectment petition with Rent Tribunal.
Cannot evict without Rent Tribunal order.
Tenant has right to contest in Rent Tribunal.
Tenant can deposit disputed rent in court if landlord refuses to accept.

RENT AGREEMENT:
Written agreement strongly recommended. Register with Rent Controller for stronger evidence.
Unregistered agreements are valid but harder to enforce in court.
Stamp duty: 0.5% of annual rent (approximately).

IF POLICE CALLED FOR FORCED EVICTION:
Call police if landlord or his agents forcibly try to evict you.
File FIR under Section 448 (house trespass) and Section 506 (criminal intimidation).
File petition in Rent Tribunal immediately.
Contact local bar association for free legal aid.

IF LANDLORD REFUSES RENT:
Always pay rent by bank transfer or cheque to have proof of payment.
If landlord refuses to accept rent: deposit in Rent Tribunal court.
Keep all receipts.
""",

"consumer_rights.txt": """CONSUMER RIGHTS IN PAKISTAN

CONSUMER PROTECTION ACTS:
Punjab Consumer Protection Act 2005, Sindh Consumer Protection Act 2014,
KPK Consumer Protection Act 2014.

CONSUMER RIGHTS:
1. Right to safe goods and services
2. Right to accurate information about products
3. Right to compensation for defective goods
4. Right to file complaint against unfair trade practices

UNFAIR TRADE PRACTICES (ILLEGAL):
- Selling expired or substandard goods
- False advertising or misleading claims
- Charging above Maximum Retail Price (MRP)
- Hoarding essential commodities

HOW TO COMPLAIN:
1. CONSUMER COURT: File written complaint. Free filing. Can award compensation.
2. PSQCA (substandard goods): 051-9244223
3. COMPETITION COMMISSION: www.cc.gov.pk (anti-competitive practices)

BANKING COMPLAINTS:
First complain to bank. If unsatisfied: Banking Mohtasib Pakistan.
Website: bankingmohtasib.gov.pk. Helpline: 111-111-266.

UTILITY COMPLAINTS:
NEPRA (electricity): nepra.org.pk
OGRA (gas): ogra.org.pk
PTCL/telecom: PTA helpline 0800-55055

ONLINE FRAUD:
File FIR under Section 420 PPC (fraud) at local police station.
File cyber complaint with FIA: complaint.fia.gov.pk or call 1991.
""",

"cyber_law.txt": """CYBER CRIMES IN PAKISTAN — PECA 2016

FIA CYBER CRIME WING HELPLINE: 1991 (24/7)
ONLINE COMPLAINT: complaint.fia.gov.pk

SECTION 20 — ONLINE HARASSMENT/DEFAMATION
Intentionally displaying false information that intimidates or harasses someone.
Punishment: imprisonment up to 3 years or fine up to Rs.1 million. NON-BAILABLE.
Includes: fake social media profiles, morphed images, blackmail, harassment campaigns.

SECTION 21 — INDECENT CONTENT WITHOUT CONSENT
Sending obscene or sexually explicit content without consent.
Punishment: 3 years or Rs.1 million fine. NON-BAILABLE.
If victim is minor: 7 years.

SECTION 3 — UNAUTHORIZED ACCESS
Gaining unauthorized access to any information system.
Punishment: 3 months or Rs.50,000 fine. NON-BAILABLE.

SECTION 11 — HATE SPEECH ONLINE
Publishing content stirring hatred based on religion, sect, race.
Punishment: 7 years. NON-BAILABLE.

HOW TO REPORT CYBER CRIMES:
1. Call FIA Cyber Crime Wing: 1991
2. File online complaint: complaint.fia.gov.pk
3. Visit nearest FIA office (in all major cities)
4. Also file FIR at local police station under relevant PPC section

EVIDENCE TO COLLECT:
- Screenshots of offensive content
- URLs/links
- Chat logs
- Email headers
- Any identifying information of the perpetrator
""",

"legal_aid.txt": """LEGAL AID AND HELPLINES IN PAKISTAN

FREE LEGAL AID:
- Pakistan Bar Council Legal Aid: Available in all district courts.
- Women cannot afford lawyer: Contact AGHS Legal Aid Cell Lahore: 042-35761999
- Punjab Legal Aid Authority: free legal aid for poor accused
- District Legal Empowerment Committee: in all districts

IMPORTANT HELPLINES:
- Police Emergency: 15
- FIA Cyber Crime: 1991
- NHRC (Human Rights): 051-9107500
- Rescue: 1122 (Punjab), 115 (Sindh)
- Domestic Violence: 1043 (Punjab Women Helpline)
- Child Protection: 0800-22444 (Sahil helpline)
- Anti-Corruption: 0800-26362 (NAB)
- Labour: 042-99231530 (Punjab Labour Department)
- Consumer: 0800-44744 (Punjab)

COURTS STRUCTURE IN PAKISTAN:
1. Supreme Court of Pakistan (Islamabad)
2. High Courts (each province + AJK + GB)
3. Sessions Courts (each district)
4. Magistrate Courts (each tehsil)
5. Special Courts: Family Court, Labour Court, Anti-Corruption, Banking Courts

TO FILE AN FIR:
Go to nearest police station (thana).
If police refuse: approach Justice of Peace under Section 22-A CrPC.
FIR is free to register. No fee is charged.
You have right to a copy of FIR immediately after registration.

IF POLICE TORTURE OR ABUSE:
File FIR against police officers at SSP office.
File complaint with NHRC: nhrc.org.pk
File Constitutional Petition in High Court under Article 199.
Contact HRCP (Human Rights Commission of Pakistan): hrcp-web.org
""",
}

def save_law_files():
    print("Saving core Pakistani law files...")
    for filename, content in CORE_LAW_DATA.items():
        filepath = RAW_DIR / filename
        filepath.write_text(content.strip(), encoding="utf-8")
        print(f"  ✓ Saved: {filename} ({len(content):,} chars)")
    print(f"\n✓ {len(CORE_LAW_DATA)} law files saved to: {RAW_DIR.absolute()}")

if __name__ == "__main__":
    print("=" * 55)
    print("Wakeel — Pakistani Law Data Collector")
    print("=" * 55)
    save_law_files()
    print("\nNext step: python rag/build_index.py")
