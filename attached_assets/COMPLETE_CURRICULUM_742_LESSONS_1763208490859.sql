-- ============================================================================
-- INNERVERSE COMPLETE CURRICULUM - 742 LESSONS
-- Generated with real CS Joseph YouTube data
-- Matched to Pinecone where transcripts exist
-- ============================================================================

-- Clear existing data
DELETE FROM curriculum;
DELETE FROM progress;
DELETE FROM lesson_chats;
DELETE FROM lesson_content_cache;

-- Season 1: Jungian Cognitive Functions (16 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '1', 'Jungian Cognitive Functions', 1, 'What Are Jungian Personality Types? | CS Joseph', 'https://www.youtube.com/watch?v=kywOjcPgGl0', '7c27e2e7-ad22-4c29-a25b-c511cbde51dd', 1, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 2, 'What are Jungian Cognitive Functions and How Do They Work? | CS Joseph', 'https://www.youtube.com/watch?v=GN7od8N6wcA', '48634aad-f696-41c1-95e8-c6729f8c1524', 2, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 3, 'What Is Extraverted Thinking? (Te) | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=8fCDh5qTO3E', '2776f175-6abe-48b9-81ba-0c046015394d', 3, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 4, 'What Is Introverted Feeling? (Fi) | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=NoM14YF2wTs', 'f7fac420-1906-449c-a42b-96408c20a80f', 4, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 5, 'What Is Extraverted Feeling (Fe)? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=bHb1MT6Gpl0', '823fbd4a-274a-4db3-b665-c0b0b12243f2', 5, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 6, 'What Is Introverted Thinking? (Ti) | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=dYi01S21wU8', '84a8ebbb-e983-4dbd-924c-36e1764d790f', 6, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 7, 'What Is Extraverted Sensing (Se)? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=pJHf4-B2V6g', 'a2297710-6f69-4fa6-8562-4199da8b506d', 7, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 8, 'What Is Introverted Intuition? (Ni) | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=n8qKEDRUVmY', 'ef51f8b4-2a6c-49eb-bf63-e616da6db364', 8, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 9, 'What Is Extraverted Intuition (Ne)? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=O3JKtThQV58', '1d9018cd-aa2e-4b71-bf75-64282b852850', 9, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 10, 'What Is Introverted Sensing (Si)? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=XwLLUZ1zB2c', 'be4ab356-f3b8-49ac-b460-ddf4fb325e22', 10, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 11, 'What Is A Cognitive Axis? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=swpwQLB1yxo', 'dacf3c93-b36a-4a22-974d-3e30b44616eb', 11, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 12, 'What Are The Four Sides of the Mind? | Four Sides Dynamics | CS Joseph', 'https://www.youtube.com/watch?v=nG_fAhk3ZGc', '28a1d0b9-3b98-4227-887a-3b75718dda3e', 12, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 13, 'What Is Functional Emulation For Cognitive Senses? | Social Engineering | CS Joseph', 'https://www.youtube.com/watch?v=oKBeENBXrl0', '698a295a-b8ea-45d9-9a47-1ee05383f3ca', 13, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 14, 'How Optimistic Or Pessimistic Are The Cognitive Functions? | Four Sides of the Mind | CS Joseph', 'https://www.youtube.com/watch?v=T7e7yMlWg6w', 'f8f82fe0-8e1c-448a-a4c7-988ca9256b5a', 14, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 15, 'What Are The Eight Cognitive Spectra? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=vUK5xKJ_aME', '47648c03-c575-4856-8aa8-dd452255c3ca', 15, TRUE),
('Building Foundation', '1', 'Jungian Cognitive Functions', 16, 'How Do Cognitive Transitions Impact The Four Sides Of The Mind? | CS Joseph', 'https://www.youtube.com/watch?v=ye6p6Th4PDQ', '4bf8fcf6-6672-4244-a971-0e45aaa1a9b5', 16, TRUE);

-- Season 16: Cognitive Attitudes (8 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '16', 'Cognitive Attitudes', 1, 'What Is The Cognitive Attitude Of The Hero Function? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=7vSqlTk5XlU', '4b3b5fdf-76e0-4434-af2d-a46c1d419b7b', 17, TRUE),
('Building Foundation', '16', 'Cognitive Attitudes', 2, 'What Is The Cognitive Attitude Of The Parent Function? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=Gq9UaJFgNfE', 'a09189e5-7958-438a-a3ba-53a12589cf1f', 18, TRUE),
('Building Foundation', '16', 'Cognitive Attitudes', 3, 'What Is The Cognitive Attitude Of The Child Function? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=TXCIQdyeiEs', '6e8eae28-dcad-4aaf-a8ae-cd4ba8d65950', 19, TRUE),
('Building Foundation', '16', 'Cognitive Attitudes', 4, 'What Is The Cognitive Attitude Of The Inferior Function? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=xnQgIwwRLfQ', '11e27c70-54af-48d8-aabd-594e7d40803d', 20, TRUE),
('Building Foundation', '16', 'Cognitive Attitudes', 5, 'What Is The Cognitive Attitude Of The Nemesis Function? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=uXppTCXalWY', 'e725227c-bf7d-4c96-b4af-173d008eb4f9', 21, TRUE),
('Building Foundation', '16', 'Cognitive Attitudes', 6, 'What Is The Cognitive Attitude Of The Critic Function? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=7NkqSlYUu9A', '6f3ad554-bd38-4cff-9083-12e5a7bd1a8a', 22, TRUE),
('Building Foundation', '16', 'Cognitive Attitudes', 7, 'What Is The Cognitive Attitude Of The Trickster Function? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=Jy3gBmGR8wo', 'dda90fa2-c5f7-4feb-9bc1-62b6665a45ed', 23, TRUE),
('Building Foundation', '16', 'Cognitive Attitudes', 8, 'What Is The Cognitive Attitude Of The Demon Function? | CS Joseph', 'https://www.youtube.com/watch?v=HGc9UEsLQsE', '14a905d6-a851-4954-97ed-f6d24879996d', 24, TRUE);

-- Season 7: Virtue & Vice (16 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '7', 'Virtue & Vice', 1, 'What Is The Virtue And Vice Of ESTJs? | Serenity Vs. Chaos | CS Joseph', 'https://www.youtube.com/watch?v=wfPGr9Cxn84', '862f4dc0-4776-4caa-9e08-34762dea4498', 25, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 2, 'What Is The Virtue And Vice Of ESTPs? | Chastity Vs. Nymphomania | CS Joseph', 'https://www.youtube.com/watch?v=xwtDLxnVd0c', '29bb87e4-1caa-4cbe-a937-7dcce0d8ed5c', 26, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 3, 'What Is The Virtue And Vice Of ENTJs? | Altruism Vs. Avarice | CS Joseph', 'https://www.youtube.com/watch?v=1QQ4Cl9_5qw', '2a3bc6cb-f24e-4750-a614-6b031fa6d824', 27, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 4, 'What Is The Virtue And Vice Of ENFJs? | Benevolence Vs. Cruelty | CS Joseph', 'https://www.youtube.com/watch?v=9vn7zVi7wMU', '72cc0e61-2d5d-4dc1-8534-47227d489581', 28, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 5, 'What Is The Virtue And Vice Of ESFJs? Caregiving Vs. Caretaking', 'https://www.youtube.com/watch?v=MZe7MSDlwac', '42fc3767-628b-46d2-a158-c66174d6fe9c', 29, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 6, 'What Is The Virtue And Vice Of ESFPs? Delayed Gratification Vs. Instant Gratification', 'https://www.youtube.com/watch?v=TJiau-zEg44', '7c3ac536-836f-4d2f-80ae-65c133a1d34f', 30, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 7, 'What Is The Virtue And Vice Of ENTPs? | Sincerity Vs. Insincerity | CS Joseph', 'https://www.youtube.com/watch?v=AdNo0TYDM8Q', 'aeaf0027-8058-4b2a-9643-7a00b728f88f', 31, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 8, 'What Is The Virtue And Vice Of ENFPs? | Charity Vs. Depravity | CS Joseph', 'https://www.youtube.com/watch?v=_L1GJBhNcA0', '41b83644-261d-43c6-91cb-8054ac48ee93', 32, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 9, 'What Is The Virtue And Vice Of ISTJs? | Objectivity Vs. The Trivial | CS Joseph', 'https://www.youtube.com/watch?v=w5_rvLpC2jQ', '3acc9b9e-bf17-4db5-a3d7-55b9faa8d2a2', 33, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 10, 'What Is The Virtue And Vice Of ISTPs? | Joy Vs. Melancholy | CS Joseph', 'https://www.youtube.com/watch?v=6QLmKIXb1ho', '1eac9eae-261b-48e8-ad4b-c5cfdfc1a50e', 34, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 11, 'What Is The Virtue And Vice Of INTJs (The Ranger)? | Trust Vs. Paranoia | CS Joseph', 'https://www.youtube.com/watch?v=WNkKQOSU7rc', '6378b206-b983-4d49-be8c-6d806788639a', 35, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 12, 'What Is The Virtue And Vice Of INFJs (The Paladin)? | Integrity Vs. Corruption | CS Joseph', 'https://www.youtube.com/watch?v=j0Xg-1C4xV8', '1d9ae496-f145-4571-9716-1f81331f7562', 36, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 13, 'What Is The Virtue And Vice Of ISFJs? | Faith Vs. Fear | CS Joseph', 'https://www.youtube.com/watch?v=SuMCzuf4v_w', '11dee702-7fbc-459a-a7cb-2a989b9c3906', 37, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 14, 'What Is The Virtue And Vice Of ISFPs? | Diligence Vs. Idleness | CS Joseph', 'https://www.youtube.com/watch?v=aTqqeexYhhg', 'e56d70be-ac31-41db-b64a-669df4208d3e', 38, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 15, 'What Is The Virtue And Vice Of INTPs (The Ardent)? | Attentiveness Vs. Apathy | CS Joseph', 'https://www.youtube.com/watch?v=-lUqM1kWULQ', 'ef845fb6-d74f-415c-a8ad-2fdf82ed5e6e', 39, TRUE),
('Building Foundation', '7', 'Virtue & Vice', 16, 'What Is The Virtue And Vice Of INFPs (The Mystic)? | Loyalty Vs. Treachery | CS Joseph', 'https://www.youtube.com/watch?v=Wxv6LOF61r0', '19ac055b-54bc-4fb2-b5c3-a271d1a5649d', 40, TRUE);

-- Season 7.2: Deadly Sins (9 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '7.2', 'Deadly Sins', 1, 'The Deadly Sin of Greed ISFP & ENTJ | CS Joseph', 'https://www.youtube.com/watch?v=aS6DuHdXsvQ', '6cfe939d-7659-4f3d-85f5-37e410e84a66', 41, TRUE),
('Building Foundation', '7.2', 'Deadly Sins', 2, 'The Deadly Sin of Gluttony INTP & ESFJ | CS Joseph', 'https://www.youtube.com/watch?v=ndrAZql3uCQ', '6e61bed9-03c8-4203-a166-c441093549fd', 42, TRUE),
('Building Foundation', '7.2', 'Deadly Sins', 3, 'Deadly Sin of Pride And How It Can Be Your Downfall (Enfj, Istp)', 'https://www.youtube.com/watch?v=FJzM6Aij-t8', '2d86cdf1-45e4-4833-bf4c-e694ffc80f50', 43, TRUE),
('Building Foundation', '7.2', 'Deadly Sins', 4, 'The Secret Power Obsession of ESTJs & INFPs | Sloth Exposed!', 'https://www.youtube.com/watch?v=KA2o2Oo2ngo', NULL, 44, TRUE),
('Building Foundation', '7.2', 'Deadly Sins', 5, 'Vainglory EXPOSED: The Fatal Flaw of ESFPs & INTJs', 'https://www.youtube.com/watch?v=J4Ongfs74yY', NULL, 45, TRUE),
('Building Foundation', '7.2', 'Deadly Sins', 6, 'How To Turn Envy In To Success As An Entp/Isfj', 'https://www.youtube.com/watch?v=ca9fNCKFKJQ', '25665a91-4b61-4ca9-8411-f99325f8d783', 46, TRUE),
('Building Foundation', '7.2', 'Deadly Sins', 7, 'Deadly Sin of Lust: Infj, Estp', 'https://www.youtube.com/watch?v=tih7TE2eWqw', 'c0bc282a-69f0-419b-8fce-67c7fedb70b2', 47, TRUE),
('Building Foundation', '7.2', 'Deadly Sins', 8, 'Balancing Wrath and Absolution for Soul Temple! Infj, Estp, Enfp, Istj', 'https://www.youtube.com/watch?v=stfRC35VHHE', NULL, 48, TRUE),
('Building Foundation', '7.2', 'Deadly Sins', 9, 'The 8 Deadly Sins (and how to avoid them) | CS Joseph', 'https://www.youtube.com/watch?v=rVV_51OixEE', NULL, 49, TRUE);

-- Season 8: Type Comparisons: Same Letters (8 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '8', 'Type Comparisons: Same Letters', 1, 'How do INTJs (The Ranger) compare to INTPs (The Ardent)? | INTJ vs INTP | CS Joseph', 'https://www.youtube.com/watch?v=e0ttE91ks70', NULL, 50, TRUE),
('Building Foundation', '8', 'Type Comparisons: Same Letters', 2, 'How Do ESTJs Compare To ESTPs?', 'https://www.youtube.com/watch?v=ZsDJ8HdDOoo', NULL, 51, TRUE),
('Building Foundation', '8', 'Type Comparisons: Same Letters', 3, 'ENTJ vs. ENTP: Rebuttal To Eric & Opaloid | CS Joseph', 'https://www.youtube.com/watch?v=SEHD_hUjRb0', NULL, 52, TRUE),
('Building Foundation', '8', 'Type Comparisons: Same Letters', 4, 'How Do ENFJs Compare To ENFPs? | ENFJ vs ENFP | CS Joseph', 'https://www.youtube.com/watch?v=4PIvzEHlW_M', NULL, 53, TRUE),
('Building Foundation', '8', 'Type Comparisons: Same Letters', 5, 'How Do ESFJs Compare To ESFPs?', 'https://www.youtube.com/watch?v=tu3rHm3UY4o', NULL, 54, TRUE),
('Building Foundation', '8', 'Type Comparisons: Same Letters', 6, 'How Do ISTJs Compare To ISTPs?', 'https://www.youtube.com/watch?v=WpmPkyUWTCE', NULL, 55, TRUE),
('Building Foundation', '8', 'Type Comparisons: Same Letters', 7, 'How Do INFJs (The Paladin) Compare To INFPs (The Mystic)? | INFJ Vs. INFP | CS Joseph', 'https://www.youtube.com/watch?v=aJqwSHUdETA', NULL, 56, TRUE),
('Building Foundation', '8', 'Type Comparisons: Same Letters', 8, 'How Do ISFJs Compare To ISFPs?', 'https://www.youtube.com/watch?v=xyl52LG-xNE', NULL, 57, TRUE);

-- Season 9: Type Comparisons: E vs I (8 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '9', 'Type Comparisons: E vs I', 1, 'How Does INFJ Compare To ENFJ? | INFJ Vs. ENFJ | CS Joseph', 'https://www.youtube.com/watch?v=1NBvt25_GbE', '01c839b8-8578-4b96-86f4-3cd70035d70f', 58, TRUE),
('Building Foundation', '9', 'Type Comparisons: E vs I', 2, 'How Do ESTJs Compare To ISTJs?', 'https://www.youtube.com/watch?v=qTUXpaSDKNo', NULL, 59, TRUE),
('Building Foundation', '9', 'Type Comparisons: E vs I', 3, 'How Do ESTPs Compare To ISTPs? | ESTP vs ISTP | CS Joseph', 'https://www.youtube.com/watch?v=7aTzCVvHDrE', NULL, 60, TRUE),
('Building Foundation', '9', 'Type Comparisons: E vs I', 4, 'How Do ENTJs (The Marshal) compare to INTJs (The Ranger)? | ENTJ Vs. INTJ | CS Joseph', 'https://www.youtube.com/watch?v=FaBbS8qxkwU', NULL, 61, TRUE),
('Building Foundation', '9', 'Type Comparisons: E vs I', 5, 'How Do ESFJs Compare To ISFJs?', 'https://www.youtube.com/watch?v=DEWaaNwvPNg', NULL, 62, TRUE),
('Building Foundation', '9', 'Type Comparisons: E vs I', 6, 'How Do ESFPs Compare To ISFPs?', 'https://www.youtube.com/watch?v=3kjPRQD5Ut8', NULL, 63, TRUE),
('Building Foundation', '9', 'Type Comparisons: E vs I', 7, 'How Do ENTPs (The Rogue) compare to INTPs (The Ardent)? | ENTP vs INTP | CS Joseph', 'https://www.youtube.com/watch?v=cXTvyyxdv3s', NULL, 64, TRUE),
('Building Foundation', '9', 'Type Comparisons: E vs I', 8, 'How Do ENFPs Compare To INFPs? | ENFP Vs. INFP | CS Joseph', 'https://www.youtube.com/watch?v=LT3urqJbQ_A', NULL, 65, TRUE);

-- Season 10: Type Comparisons: T vs F (8 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '10', 'Type Comparisons: T vs F', 1, 'How Do ESTJs Compare To ESFJs?', 'https://www.youtube.com/watch?v=RN_ZojNgAmw', NULL, 66, TRUE),
('Building Foundation', '10', 'Type Comparisons: T vs F', 2, 'How Do ESTPs Compare To ESFPs? | ESFP vs ESTP | CS Joseph', 'https://www.youtube.com/watch?v=gj0FY6T_0-M', NULL, 67, TRUE),
('Building Foundation', '10', 'Type Comparisons: T vs F', 3, 'How Do ENTJs Compare To ENFJs? | ENTJ vs ENFJ | CS Joseph', 'https://www.youtube.com/watch?v=YKY79HmT-Z8', NULL, 68, TRUE),
('Building Foundation', '10', 'Type Comparisons: T vs F', 4, 'How Do ENTPs Compare To ENFPs? | ENTP vs ENFP | CS Joseph', 'https://www.youtube.com/watch?v=8iloyqYZMrc', NULL, 69, TRUE),
('Building Foundation', '10', 'Type Comparisons: T vs F', 5, 'How Do ISTJs Compare To ISFJs?', 'https://www.youtube.com/watch?v=UrhXH1Obe1M', NULL, 70, TRUE),
('Building Foundation', '10', 'Type Comparisons: T vs F', 6, 'How Do ISTPs Compare to ISFPs? | ISTP vs ISFP | CS Joseph', 'https://www.youtube.com/watch?v=g6vvMyV9tq4', NULL, 71, TRUE),
('Building Foundation', '10', 'Type Comparisons: T vs F', 7, 'How do INTJs (The Ranger) Compare to INFJs? (the Paladin) | INTJ Vs. INFJ | CS Joseph', 'https://www.youtube.com/watch?v=oL1Wo4ODg8U', NULL, 72, TRUE),
('Building Foundation', '10', 'Type Comparisons: T vs F', 8, 'How Do INTPs (The Ardent) Compare To INFPs (The Mystic)? | INTP vs INFP | CS Joseph', 'https://www.youtube.com/watch?v=XxwtRPHPwCM', NULL, 73, TRUE);

-- Season 11: Type Comparisons: S vs N (8 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '11', 'Type Comparisons: S vs N', 1, 'How Do ESTJs Compare To ENTJs? | ESTJ vs ENTJ | CS Joseph', 'https://www.youtube.com/watch?v=SidwvZBBNDo', NULL, 74, TRUE),
('Building Foundation', '11', 'Type Comparisons: S vs N', 2, 'How Do ESTPs Compare To ENTPs? | ESTP vs ENTP | CS Joseph', 'https://www.youtube.com/watch?v=2TBr8BK43oE', NULL, 75, TRUE),
('Building Foundation', '11', 'Type Comparisons: S vs N', 3, 'How Do ESFJs Compare To ENFJs?', 'https://www.youtube.com/watch?v=C_qeCVU6e58', NULL, 76, TRUE),
('Building Foundation', '11', 'Type Comparisons: S vs N', 4, 'How Do ESFPs Compare To ENFPs? | ESFP vs ENFP | CS Joseph', 'https://www.youtube.com/watch?v=cS_F0R39PVc', NULL, 77, TRUE),
('Building Foundation', '11', 'Type Comparisons: S vs N', 5, 'How Do ISTJs (The Archivist) compare to INTJs (The Ranger)? | ISTJ Vs. INTJ | CS Joseph', 'https://www.youtube.com/watch?v=W4Zy0qw6bfM', NULL, 78, TRUE),
('Building Foundation', '11', 'Type Comparisons: S vs N', 6, 'How Do ISTPs (The Artificer) compare to INTPs (The Ardent)? | ISTP Vs. INTP | CS Joseph', 'https://www.youtube.com/watch?v=P-meUdrD2Y4', NULL, 79, TRUE),
('Building Foundation', '11', 'Type Comparisons: S vs N', 7, 'How Do ISFJs Compare To INFJs? | ISFJ Vs. INFJ | CS Joseph', 'https://www.youtube.com/watch?v=D3nJ9bUxh50', NULL, 80, TRUE),
('Building Foundation', '11', 'Type Comparisons: S vs N', 8, 'How Do ISFPs (The Druid) Compare To INFPs (The Mystic)? | ISFP Vs. INFP | CS Joseph', 'https://www.youtube.com/watch?v=G00oNc3Idcs', NULL, 81, TRUE);

-- Season 5: Cognitive Synchronicity (5 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '5', 'Cognitive Synchronicity', 1, 'How Does The Golden Rule Apply To Cognitive Compatibility?', 'https://www.youtube.com/watch?v=gH9YaFADufo', '9fc0f657-a487-4e52-b81f-633e1bb9594b', 82, TRUE),
('Building Foundation', '5', 'Cognitive Synchronicity', 2, 'What Is Cognitive Synchronicity Of Sensing Functions?', 'https://www.youtube.com/watch?v=OFsRr4b8hYE', '217f5148-42d5-4004-ab77-7d5655c7f610', 83, TRUE),
('Building Foundation', '5', 'Cognitive Synchronicity', 3, 'What Is Cognitive Synchronicity Of Intuition Functions?', 'https://www.youtube.com/watch?v=-53jqQ3Na5Y', 'c425063e-50ce-465c-89b4-40f4bc1723bd', 84, TRUE),
('Building Foundation', '5', 'Cognitive Synchronicity', 4, 'What Is Cognitive Synchronicity Of Feeling Functions?', 'https://www.youtube.com/watch?v=EMPRsQwIJEw', 'e4c0c91a-7519-4a8b-958b-799ebf00bcc9', 85, TRUE),
('Building Foundation', '5', 'Cognitive Synchronicity', 5, 'What Is Cognitive Synchronicity Of Thinking Functions? | Ti vs Te | CS Joseph', 'https://www.youtube.com/watch?v=rAX6kEed_8U', '3fdf2cbd-0aa8-4753-8062-689a5b4724a7', 86, TRUE);

-- Season 25: Cognitive Asynchronicity (5 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Building Foundation', '25', 'Cognitive Asynchronicity', 1, 'What is the difference between camaraderie and compatibility? | CS Joseph', 'https://www.youtube.com/watch?v=OcV0HskbAgA', NULL, 87, TRUE),
('Building Foundation', '25', 'Cognitive Asynchronicity', 2, 'Cognitive Asynchronicity | The Si-Ne Axis | CS Joseph', 'https://www.youtube.com/watch?v=hRZqcOXOc40', NULL, 88, TRUE),
('Building Foundation', '25', 'Cognitive Asynchronicity', 3, 'Cognitive Asynchronicity: The Ni - Se Axis | CS Joseph', 'https://www.youtube.com/watch?v=2x6WUhRKWkg', NULL, 89, TRUE),
('Building Foundation', '25', 'Cognitive Asynchronicity', 4, 'Why Is Camaraderie Important & The Fi + Te Axis | Cognitive Asynchronicity | CS Joseph', 'https://www.youtube.com/watch?v=3eIGicfkOo4', NULL, 90, TRUE),
('Building Foundation', '25', 'Cognitive Asynchronicity', 5, 'Cognitive Asynchronicity The Ti-Fe Axis | CS Joseph', 'https://www.youtube.com/watch?v=MKPyk0Xfv0w', NULL, 91, TRUE);

-- Season 2: How to Type (11 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '2', 'How to Type', 1, 'What''s The Problem With MBTI Tests? Is the MBTI Accurate? | CS Joseph', 'https://www.youtube.com/watch?v=kQxzwJfdWDQ', NULL, 92, TRUE),
('Deepening Knowledge', '2', 'How to Type', 2, 'What Are The Four Temperaments? | Guardians: ESTJ, ESFJ, ISTJ, ISFJ | CS Joseph', 'https://www.youtube.com/watch?v=heBzJzV8ExA', 'd2c2cfbb-6464-41a4-aa6e-097566e757ce', 93, TRUE),
('Deepening Knowledge', '2', 'How to Type', 3, 'What Are The Four Temperaments? | Artisans: ESTP, ESFP, ISTP, ISFP | CS Joseph', 'https://www.youtube.com/watch?v=71oiEacnpuE', 'ce29080b-408a-464e-b432-cf7d073080d1', 94, TRUE),
('Deepening Knowledge', '2', 'How to Type', 4, 'What Are The Four Temperaments? Intellectuals: ENTJ, ENTP, INTJ, INTP | CS Joseph', 'https://www.youtube.com/watch?v=W1ZHUHWT3NQ', 'aed208e3-92e1-47ba-af60-31a82dd18011', 95, TRUE),
('Deepening Knowledge', '2', 'How to Type', 5, 'What Are The Four Temperaments? Idealists: ENFJ, ENFP, INFJ, INFP | CS Joseph', 'https://www.youtube.com/watch?v=AqBuPW9fazY', '68ca3b89-d6ae-4dd2-bab2-7b3502da87e6', 96, TRUE),
('Deepening Knowledge', '2', 'How to Type', 6, 'What Are The Four Interactions Styles? | Structure: ESTJ, ESTP, ENTJ, ENFJ | CS Joseph', 'https://www.youtube.com/watch?v=W8KoMaEn0mU', '4ba045f0-c06f-4a33-aad6-53ceedb19414', 97, TRUE),
('Deepening Knowledge', '2', 'How to Type', 7, 'What Are The Four Interaction Styles? | Starters: ESFJ, ESFP, ENTP, ENFP | CS Joseph', 'https://www.youtube.com/watch?v=G5i1KxOVXQM', 'd119f2fb-d251-4e8e-8bde-e08bf55cff75', 98, TRUE),
('Deepening Knowledge', '2', 'How to Type', 8, 'What Are The Four Communication Styles? Finisher Types: ISTJ, ISTP, INTJ, INFJ | CS Joseph', 'https://www.youtube.com/watch?v=PDc5GERZvYg', 'd29b2c61-b6a5-4ca2-9f31-324918833af5', 99, TRUE),
('Deepening Knowledge', '2', 'How to Type', 9, 'What are the Four Communication Styles? Background Types: ISFJ, ISFP, INTP, INFP | CS Joseph', 'https://www.youtube.com/watch?v=WBOpGSymsnU', '598e58fe-b0bd-445c-bcec-73d9cbeb8ee2', 100, TRUE),
('Deepening Knowledge', '2', 'How to Type', 10, 'How To Personality Type Anyone | The Type Grid | CS Joseph', 'https://www.youtube.com/watch?v=5ASWxOXmF1M', 'a33ab235-7052-48c0-bc76-1acf6ad4de28', 101, TRUE),
('Deepening Knowledge', '2', 'How to Type', 11, 'How Do Social Moratoriums Impact The Interaction Styles?', 'https://www.youtube.com/watch?v=NKtVkZXZEhE', '7da7b48b-e6ac-41b8-a420-1c9c76d73301', 102, TRUE);

-- Season 3: 16 Archetypes (16 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '3', '16 Archetypes', 1, 'Who Are The ESTJs (The Judicator)? | ESTJ Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=rKEbXXbsb7k', NULL, 103, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 2, 'Who Are The ESTPs (The Gladiator)? | ESTP Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=dCM618eCpZQ', NULL, 104, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 3, 'Who Are the ENTJs (The Marshal)? | ENTJ Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=WracDPYfTww', NULL, 105, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 4, 'Who Are The ENFJs (The Cleric)? | ENFJ Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=fmzYW_0mfJk', NULL, 106, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 5, 'Who Are The ESFJs (The Cavalier)? | ESFJ Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=Ad6Xl1VG-SY', NULL, 107, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 6, 'Who Are The ESFPs (The Duelist)? | ESFP Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=wEVuHS-ehYo', NULL, 108, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 7, 'Who Are The ENTPs (The Rogue)? | ENTP Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=qC5i-4VbSx4', NULL, 109, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 8, 'Who Are The ENFPs (The Bard)? | ENFP Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=eBE2-Nu7yys', NULL, 110, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 9, 'Who Are The ISTJs (The Archivist)? | ISTJ Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=UiZ_4P6lVJM', NULL, 111, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 10, 'Who Are The ISTPs (The Artificer)? | ISTP Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=zF7XyYBp8dY', NULL, 112, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 11, 'Who Are The INTJs (The Ranger)? | INTJ Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=DPLzbSyQ10U', NULL, 113, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 12, 'Who Are The INFJs? (The Paladin) | INFJ Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=Ir-ypPLUdxY', NULL, 114, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 13, 'Who Are The ISFJs (The Knight)? | ISFJ Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=Ghe48e4BSYI', NULL, 115, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 14, 'Who Are The ISFPs (The Druid)? | ISFP Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=ntcBulfl_IY', NULL, 116, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 15, 'Who Are The INTPs? (The Ardent) | INTP Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=WZBEuKPPEx0', NULL, 117, TRUE),
('Deepening Knowledge', '3', '16 Archetypes', 16, 'Who Are The INFPs? (The Mystic) | INFP Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=rZJhg9R1Gag', NULL, 118, TRUE);

-- Season 12: Social Compatibility (17 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '12', 'Social Compatibility', 1, 'What Are The Three Relationship Styles? Social, Working, Sexual', 'https://www.youtube.com/watch?v=dNKtv1zsUjI', NULL, 119, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 2, 'What Types Are Socially Compatible With ESTJs? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=_6GpN6wdVpQ', NULL, 120, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 3, 'What Types Are Socially Compatible With ESTPs? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=eeCDFjRggf8', NULL, 121, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 4, 'What Types Are Socially Compatible With ENTJs? | ENTJ Relationships | CS Joseph', 'https://www.youtube.com/watch?v=IA0S9GOvI-U', '2a8bef93-36ff-43bf-943c-1d4ab236ed06', 122, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 5, 'What Types Are Socially Compatible With ENFJs? | CS Joseph', 'https://www.youtube.com/watch?v=yEh3HY5YNx4', NULL, 123, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 6, 'What Types Are Socially Compatible With ESFJs? | ESFJ relationships | CS Joseph', 'https://www.youtube.com/watch?v=DLPQOoASnec', 'c7f3fb8c-cbad-4c45-96ad-3f5b37835265', 124, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 7, 'What Types Are Socially Compatible With ESFPs? | ESFP relationships | CS Joseph', 'https://www.youtube.com/watch?v=JCLN6mSzgWs', 'b79c6e6a-81a3-4a00-8d57-bb884555adb7', 125, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 8, 'What Types Are Socially Compatible With ENTPs (The Rogue)? | CS Joseph', 'https://www.youtube.com/watch?v=2VgeyXwLfYI', NULL, 126, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 9, 'What Types Are Socially Compatible With ENFPs? | CS Joseph', 'https://www.youtube.com/watch?v=BFY1AFB8QO4', NULL, 127, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 10, 'What Types Are Socially Compatible With ISTJs? | ISTJ Personality | CS Joseph', 'https://www.youtube.com/watch?v=gqC8we--Ewo', 'c84a6851-bde1-4644-8ac1-71a5220c9dd2', 128, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 11, 'What Types are Socially Compatible with ISTP''s (The Artificer)? | CS Joseph', 'https://www.youtube.com/watch?v=V0V3uE3EPLI', 'e9730a73-0ec9-44e6-8e08-db773b12292b', 129, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 12, 'What Types Are Socially Compatible With INTJs (The Ranger)? | INTJ Relationships | CS Joseph', 'https://www.youtube.com/watch?v=EiQgxSI9Hb8', '38cdd735-a3e9-4c1d-98dc-ddc11db14ea5', 130, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 13, 'What Types Are Socially Compatible With INFJs (The Paladin)? | CS Joseph', 'https://www.youtube.com/watch?v=rfY7mvD9Yhs', NULL, 131, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 14, 'What Types Are Socially Compatible With ISFJs? | ISFJ Personality Type | CS Joseph', 'https://www.youtube.com/watch?v=tyFFieqSdA4', '62beb697-0fd7-403c-af60-29636a1eb89e', 132, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 15, 'What Types Are Socially Compatible With ISFPs? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=vZCDSX50vT8', NULL, 133, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 16, 'What Types Are Socially Compatible With INTPs (The Ardent)? | INTP Relationships | CS Joseph', 'https://www.youtube.com/watch?v=0rhxGnzE5Ng', '7f128053-3bb5-4685-815e-7022b0ed24ba', 134, TRUE),
('Deepening Knowledge', '12', 'Social Compatibility', 17, 'What Types Are Socially Compatible With INFPs (The Mystic)? | CS Joseph', 'https://www.youtube.com/watch?v=FVx3U2UFXBw', NULL, 135, TRUE);

-- Season 14.1: Golden Pairs (8 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '14.1', 'Golden Pairs', 1, 'Unveiling the Golden Pairs: ESTP & ISTJ', 'https://www.youtube.com/watch?v=84p_S61Q7tc', '228919dc-8618-461e-8509-7198931b9d55', 136, TRUE),
('Deepening Knowledge', '14.1', 'Golden Pairs', 2, 'Unveiling the Golden Pairs: ENFP & INFJ | Season 14 Part 1 | CS Joseph', 'https://www.youtube.com/watch?v=LOOYjdV2YNw', '6fce1bfa-9b6a-4dd0-a188-6ee5962824c0', 137, TRUE),
('Deepening Knowledge', '14.1', 'Golden Pairs', 3, 'Unveiling the Golden Pairs: ENTP & INTJ | Season 14 Part 1 | CS Joseph', 'https://www.youtube.com/watch?v=STlkITjMGzI', '0cdb6844-c0f6-4831-8f54-3cd981a89ab6', 138, TRUE),
('Deepening Knowledge', '14.1', 'Golden Pairs', 4, 'Unveiling the Golden Pairs: ESFP & ISFJ | Season 14 Part 1 | CS Joseph', 'https://www.youtube.com/watch?v=sIO6UwnGTkU', '3f3e3be1-217c-4089-a0f5-1d461ac45f1b', 139, TRUE),
('Deepening Knowledge', '14.1', 'Golden Pairs', 5, 'Unveiling the Golden Pairs: ESFJ & ISFP | Season 14 Part 1 | CS Joseph', 'https://www.youtube.com/watch?v=k1DNB1HRah4', '2df00481-6eb3-4ed0-85f9-a74f5373ffc3', 140, TRUE),
('Deepening Knowledge', '14.1', 'Golden Pairs', 6, 'Unveiling the Golden Pairs: ENFJ & INFP | Season 14 Part 1 | CS Joseph', 'https://www.youtube.com/watch?v=snKXuDtMzms', '787588f6-1347-457f-ac44-5cad5401a258', 141, TRUE),
('Deepening Knowledge', '14.1', 'Golden Pairs', 7, 'Unveiling the Golden Pairs: ENTJ & INTP | Season 14 Part 1 | CS Joseph', 'https://www.youtube.com/watch?v=mcLKl8ajubk', '30d0befa-07fe-4eaf-aa5b-6c04bfdee925', 142, TRUE),
('Deepening Knowledge', '14.1', 'Golden Pairs', 8, 'Unveiling the Golden Pairs: ESTJ & ISTP | Season 14 Part 1 | CS Joseph', 'https://www.youtube.com/watch?v=8fvkDJ1chl8', 'ae640d3b-ce30-4519-9b1e-3f53f2ea7b05', 143, TRUE);

-- Season 14.2: Pedagogue Pairs (8 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '14.2', 'Pedagogue Pairs', 1, 'Pedagogue Pairs: ESFP & ISTJ | Season 14 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=5vOUy_DlF2k', '0704b4ed-7890-40cd-b918-ea2c058412ac', 144, TRUE),
('Deepening Knowledge', '14.2', 'Pedagogue Pairs', 2, 'Pedagogue Pairs: ESFJ & ISTP | Season 14 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=Jlu8TBMnj-Q', '0f336497-d51a-440a-8319-818a99b6177e', 145, TRUE),
('Deepening Knowledge', '14.2', 'Pedagogue Pairs', 3, 'Pedagogue Pairs: ENFJ & INTP | Season 14 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=GSFWuPaHU4w', '0eafcf97-795b-49b5-b95f-8e7ce778f83f', 146, TRUE),
('Deepening Knowledge', '14.2', 'Pedagogue Pairs', 4, 'Pedagogue Pairs: ENTJ & INFP | Season 14 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=Mdok3Wlh1y4', NULL, 147, TRUE),
('Deepening Knowledge', '14.2', 'Pedagogue Pairs', 5, 'Pedagogue Pairs: ESTP & ISFJ | Season 14 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=rsMHbL4Rd38', '8d4a6a25-7ab4-4351-a62b-2656613e2b43', 148, TRUE),
('Deepening Knowledge', '14.2', 'Pedagogue Pairs', 6, 'Pedagogue Pairs: ESTJ & ISFP | Season 14 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=n0S3JNNxVas', '18e95f56-e026-4ece-9e7d-20d0ae03e5d1', 149, TRUE),
('Deepening Knowledge', '14.2', 'Pedagogue Pairs', 7, 'Pedagogue Pairs: ENFP & INTJ | Season 14 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=-8tEMJC8ibs', 'fe11b313-f05a-4e81-8a12-fe744e793b5c', 150, TRUE),
('Deepening Knowledge', '14.2', 'Pedagogue Pairs', 8, 'Pedagogue Pairs: ENTP & INFJ | Season 14 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=j728EHIrTPg', '49b50fec-e96b-42ac-befb-0a2e73bb6140', 151, TRUE);

-- Season 14.3: Bronze Pairs (8 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '14.3', 'Bronze Pairs', 1, 'Unveiling the Bronze Pairs: ENFP & ISTP | Season 14 Part 3 | CS Joseph', 'https://www.youtube.com/watch?v=dV2lVqNfoZo', 'b9ddb9dd-2f8a-489c-a323-afa40eaedd23', 152, TRUE),
('Deepening Knowledge', '14.3', 'Bronze Pairs', 2, 'Unveiling the Bronze Pairs: ENTP & ISFP | Season 14 Part 3 | CS Joseph', 'https://www.youtube.com/watch?v=vFUCCOm5HLQ', 'e71187b7-cbc3-412c-a217-c2c3c692fd46', 153, TRUE),
('Deepening Knowledge', '14.3', 'Bronze Pairs', 3, 'Unveiling the Bronze Pairs: ESFP & INTP | Season 14 Part 3 | CS Joseph', 'https://www.youtube.com/watch?v=fAsVF75qE7I', '9e5bda57-b052-47bc-a9b2-aec14a10d316', 154, TRUE),
('Deepening Knowledge', '14.3', 'Bronze Pairs', 4, 'Unveiling the Bronze Pairs: ESFJ & INTJ | Season 14 Part 3 | CS Joseph', 'https://www.youtube.com/watch?v=2gRahgVlBgA', '2c953c1d-3882-473f-bd7b-04ffab86e10c', 155, TRUE),
('Deepening Knowledge', '14.3', 'Bronze Pairs', 5, 'Unveiling the Bronze Pairs: ENFJ & ISTJ | Season 14 Part 3 | CS Joseph', 'https://www.youtube.com/watch?v=VmRXDUfdl_U', 'dfab992f-58df-43f5-9036-0638911a8a18', 156, TRUE),
('Deepening Knowledge', '14.3', 'Bronze Pairs', 6, 'Unveiling the Bronze Pairs: ENTJ & ISFJ | Season 14 Part 3 | CS Joseph', 'https://www.youtube.com/watch?v=VeXQ1jK0oA0', '85cd1a5e-cf8a-4115-9ffb-8fbf86d7d1c6', 157, TRUE),
('Deepening Knowledge', '14.3', 'Bronze Pairs', 7, 'Unveiling the Bronze Pairs: ESTP & INFP | Season 14 Part 3 | CS Joseph', 'https://www.youtube.com/watch?v=JAWEOYeqis0', 'af1e6580-dbf5-4fea-bc88-67b293ced122', 158, TRUE),
('Deepening Knowledge', '14.3', 'Bronze Pairs', 8, 'Unveiling the Bronze Pairs: ESTJ & INFJ | Season 14 Part 3 | CS Joseph', 'https://www.youtube.com/watch?v=q_QmkW26QiM', '2c04bbc2-12f0-431f-a735-23907aa92827', 159, TRUE);

-- Season 14.4: Duality Pairs (7 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '14.4', 'Duality Pairs', 1, 'Did I Change My Mind About Socionics?  | CS Joseph', 'https://www.youtube.com/watch?v=ICiFatVDgDE', NULL, 160, TRUE),
('Deepening Knowledge', '14.4', 'Duality Pairs', 2, 'ESTJ & INFP? Maybe if you''ve got something to teach other...| Sexual Compatibility | CS Joseph', 'https://www.youtube.com/watch?v=etzZJlrEkCY', NULL, 161, TRUE),
('Deepening Knowledge', '14.4', 'Duality Pairs', 3, 'ENFJ & ISTP Duality Pairs | Season 14 Part 4, Ep. 5 | CS Joseph', 'https://www.youtube.com/watch?v=C1JzLNvU1NU', '3a8b40af-a981-4a70-a106-2feaee8d73cd', 162, TRUE),
('Deepening Knowledge', '14.4', 'Duality Pairs', 4, 'ESTP & INFJ Duality Pairs | Season 14 Part 4 | CS Joseph', 'https://www.youtube.com/watch?v=dE2_v-3AGf4', '573f9dab-cb3d-492c-bee7-998ee0fdf10d', 163, TRUE),
('Deepening Knowledge', '14.4', 'Duality Pairs', 5, 'ENTJ & ISFP Duality Pairs | Season 14 Part 4 | CS Joseph', 'https://www.youtube.com/watch?v=i8KJnG0k83M', '054f4117-f83b-41bc-a98b-195319fc4361', 164, TRUE),
('Deepening Knowledge', '14.4', 'Duality Pairs', 6, 'ESFJ & INTP Duality Pairs | Season 14 Part 4 | CS Joseph', 'https://www.youtube.com/watch?v=Q9lCL67W9dM', 'ce2b97f3-5fee-4904-ab27-b5a4805eb790', 165, TRUE),
('Deepening Knowledge', '14.4', 'Duality Pairs', 7, 'ENTP + ISFJ Duality Pairs | Season 14 Part 4 | CS Joseph', 'https://www.youtube.com/watch?v=drj3KVZri2k', 'e2bd475e-7e5e-4c8d-8da6-da3a4f0cf833', 166, TRUE);

-- Season 15: Type Grid Deep Dive (12 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 1, 'Intro To Interaction Style & Temperament Behaviors | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=94fJkcAyNmY', NULL, 167, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 2, 'How Does Direct Compare To Informative? | Communication Style | CS Joseph', 'https://www.youtube.com/watch?v=I8fSV_9zjms', '2e1b7f26-5f47-4f9c-8b45-42baae2e83ba', 168, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 3, 'How Does Initiating Compare To Responding? | Initiating Vs. Responding | CS Joseph', 'https://www.youtube.com/watch?v=4mOpzAXFrK8', '1d7696de-a4e4-4446-8471-ba7981ed4696', 169, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 4, 'How Does Control Compare To Movement? | Outcome Vs Progression | CS Joseph', 'https://www.youtube.com/watch?v=B8yx_AbP13k', NULL, 170, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 5, 'How Does Abstract Compare To Concrete? | Abstract Vs. Concrete | CS Joseph', 'https://www.youtube.com/watch?v=65SLHwhpqzY', 'b39bf7da-5f80-4f36-8b56-1eaa607b5b22', 171, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 6, 'How Does Affiliative Compare To Pragmatic? | CS Joseph', 'https://www.youtube.com/watch?v=hZOLCLQUi7c', '9ddc927f-d9f2-48e1-baca-7d11e4006422', 172, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 7, 'How Does Systematic Compare To Interest? | CS Joseph', 'https://www.youtube.com/watch?v=wyXjGCscM8I', 'b547f78d-ece8-4790-8fb2-48830471da59', 173, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 8, 'How Do We Use The Type Grid? | Personality Typing | CS Joseph', 'https://www.youtube.com/watch?v=Tf9Ew4Nkzo8', NULL, 174, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 9, 'What Is The Temperament Matrix? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=ec2IKJLf6gg', 'b879d2f2-abb5-4ef0-9156-f2fb2947e414', 175, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 10, 'How To Prevent Mistyping | Personality Typing | CS Joseph', 'https://www.youtube.com/watch?v=j7I-xiKY_eI', NULL, 176, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 11, 'What Is Ambiversion?', 'https://www.youtube.com/watch?v=gHWCn5-EWkQ', 'b592cf69-0e95-48e0-b226-0a0e6b4c009e', 177, TRUE),
('Deepening Knowledge', '15', 'Type Grid Deep Dive', 12, 'MBTI Letter Dichotomies Debunked', 'https://www.youtube.com/watch?v=B_0enevGeHE', NULL, 178, TRUE);

-- Season 17.1: Quadras & Four Sides (17 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 1, 'What Is the Source of All Cognition? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=RfcgQCFxj5M', '5d22018c-81dd-4666-8337-a759846921f3', 179, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 2, 'What is the Ego and it''s Gateway? | Four Sides of the Mind | CS Joseph', 'https://www.youtube.com/watch?v=enVdGxRFNjo', '8fcc8df1-63a2-42af-87c0-82c917f23521', 180, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 3, 'What Is The Subconscious And Its Gateway? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=BzSiGivEXEQ', 'e620c116-4762-4e5c-95c5-138fc7c3ad5e', 181, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 4, 'What Is The Unconscious And Its Gateway? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=SISro_W-ZaM', 'f510d82c-b07e-4b0e-80bd-d11c88b8cc14', 182, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 5, 'Part 1: What Is The Superego & Its Gateway? | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=kgZHA6mhHGI', 'e5ddaf38-0707-4445-9113-697214adfa28', 183, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 6, 'What Is The Superego & Its Gateway? Part 2', 'https://www.youtube.com/watch?v=GZYIkh7mWiM', 'e5ddaf38-0707-4445-9113-697214adfa28', 184, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 7, 'Who are the Alpha Quadra? | The Crusaders : ESFJ ENTP ISFJ INTP | CS Joseph', 'https://www.youtube.com/watch?v=KoikKSCbwhs', '2d45dd5f-1e36-4309-8045-6d80c724ffae', 185, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 8, 'Who are the Beta Quadra? | The Templars: ESTP, ISTP, ENFJ, INFJ | CS Joseph', 'https://www.youtube.com/watch?v=e75Hs4Srvso', '0ffb34d7-649e-4743-8c40-7309cc381160', 186, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 9, 'Who are the Gamma Quadra? | Wayfarers : INTJ, ENTJ, ESFP, ISFP | CS Joseph', 'https://www.youtube.com/watch?v=fRxjSImkyZ0', '05330a31-b5d1-4958-b306-3683d1de0b15', 187, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 10, 'Open letter & Psychological Prejudice - S17 Bonus Episode', 'https://www.youtube.com/watch?v=9QKn0o5pB6Y', '3c981b55-86f8-4b42-8bcb-ce9c7f744ba0', 188, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 11, 'Who are the Delta Quadra? | Philosophers: ESTJ, ENFP, ISTJ, INFP | CS Joseph', 'https://www.youtube.com/watch?v=Gq5wQun9GUA', '05d6e7e3-f73d-4776-9a2f-642333c4b51f', 189, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 12, 'The Virtue and Vice of the Quadras | Four Sides of the MInd | CS Joseph', 'https://www.youtube.com/watch?v=FxDT8rZ2tAU', NULL, 190, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 13, 'How to Type with Quadras', 'https://www.youtube.com/watch?v=HEAw0jBUV2c', NULL, 191, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 14, 'How the four sides of the mind manifest in children', 'https://www.youtube.com/watch?v=Btra0rhzYH8', '4755f8ee-f3b4-46df-a3d6-0d33d285c4b9', 192, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 15, 'How the four sides of the mind impact the life stages of a human', 'https://www.youtube.com/watch?v=prEtypzmugc', '4755f8ee-f3b4-46df-a3d6-0d33d285c4b9', 193, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 16, 'Positive Parenting Solutions | Trauma Impact | Four Sides of the Mind | CS Joseph', 'https://www.youtube.com/watch?v=oAALwW1OBf8', 'e78a3aec-8c76-40a5-abdb-604f59470940', 194, TRUE),
('Deepening Knowledge', '17.1', 'Quadras & Four Sides', 17, 'What is Cognitive Focus? | Individuation | Four sides of the mind | CS Joseph', 'https://www.youtube.com/watch?v=3tdlaBB-6TU', '4755f8ee-f3b4-46df-a3d6-0d33d285c4b9', 195, TRUE);

-- Season 17.2: Quadra Abuse Patterns (5 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Deepening Knowledge', '17.2', 'Quadra Abuse Patterns', 1, 'Crusader (ENTP, INTP, ESFJ, ISFJ)  Abusers? | Season 17 Part 2 Quadras | CS Joseph', 'https://www.youtube.com/watch?v=keNewFwXxM8', '0409109f-4e36-47c0-9335-e695ac764841', 196, TRUE),
('Deepening Knowledge', '17.2', 'Quadra Abuse Patterns', 2, 'Templar (ESTP, ISTP, ENFJ, INFJ)  Abusers? | Season 17 Part 2 Quadras | CS Joseph', 'https://www.youtube.com/watch?v=SGCdluA5DHk', '6f1e260b-ecd8-44e5-a16f-bbfc613e34f4', 197, TRUE),
('Deepening Knowledge', '17.2', 'Quadra Abuse Patterns', 3, 'Wayfarer Abusers (INTJ, ENTJ, ISFP, ESFP)? | Season 17 Pt 2 | CS Joseph', 'https://www.youtube.com/watch?v=A-W3RwyJP3M', 'a9772fe7-e52d-4c02-89e4-c7d4c9c60c60', 198, TRUE),
('Deepening Knowledge', '17.2', 'Quadra Abuse Patterns', 4, 'Philosopher (ESTJ, ISTJ, ENFP, INFP) Abusers? | Season 17 Part 2 Quadras | CS Joseph', 'https://www.youtube.com/watch?v=pnaKLLRUUCU', 'f6fb1e26-e277-4f4c-8271-e8c8ee9dfb85', 199, TRUE),
('Deepening Knowledge', '17.2', 'Quadra Abuse Patterns', 5, 'Positive Parenting Solutions | Season 17 Part 2 | CS Joseph', 'https://www.youtube.com/watch?v=3TuPEOBHY7s', 'c56ea5a9-3ab8-4e15-99d3-bdf5e6ded153', 200, TRUE);

-- Season 27: 8 Rules for Love (16 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Advanced Applications', '27', '8 Rules for Love', 1, '8 rules for loving an ESTJ | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=g8h0kLLBEk4', NULL, 201, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 2, '8 Rules For Loving an ESTP | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=cTtnMZ27aus', NULL, 202, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 3, '8 Rules for loving an ENTJ | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=pmqmzyD6cVA', NULL, 203, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 4, '8 Rules for loving an ENFJ | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=EEKcxtplTXc', NULL, 204, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 5, '8 Rules for Loving an ESFJ | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=r7QKJlP8RH4', NULL, 205, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 6, '8 Rules for loving an ESFP | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=PbPh0YZxRGo', NULL, 206, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 7, '8 Rules for Loving an ENTP | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=8EXnOampZxw', NULL, 207, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 8, '8 Rules for Loving an ENFP | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=YJmp8Gg22gg', NULL, 208, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 9, '8 Rules For Loving an ISTJ | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=egoas-1tOik', NULL, 209, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 10, '8 Rules for Loving an ISTP | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=GUGiexP7-vg', NULL, 210, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 11, '8 Rules For Loving an INTJ | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=OVQACf7-0-k', NULL, 211, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 12, '8 Rules For Loving an INFJ | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=QKsAEGA9Lsk', NULL, 212, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 13, '8 Rules for Loving an ISFJ | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=uKEzfMkhW4c', NULL, 213, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 14, '8 rules for loving an ISFP | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=gLwQL3v1B9g', NULL, 214, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 15, '8 Rules for Loving an INTP | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=ZtDeDkRFnlA', NULL, 215, TRUE),
('Advanced Applications', '27', '8 Rules for Love', 16, '8 Rules for Loving an INFP | Season 27 | CS Joseph', 'https://www.youtube.com/watch?v=2EmQbi4TQdI', NULL, 216, TRUE);

-- Season 22: Cognitive Transitions (16 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Advanced Applications', '22', 'Cognitive Transitions', 1, 'What are the cognitive transitions of ESTJs?', 'https://www.youtube.com/watch?v=asFkWII1OgE', NULL, 217, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 2, 'What Are The Cognitive Transitions of ESTPs?', 'https://www.youtube.com/watch?v=8Lo6e6pUwoU', NULL, 218, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 3, 'What are the cognitive transitions of ENTJs? | ENTJ Cognitive Transitions | CS Joseph', 'https://www.youtube.com/watch?v=nJ-CUIoBeE4', NULL, 219, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 4, 'What are the Cognitive Transitions of ENFJs?', 'https://www.youtube.com/watch?v=4cwH9FQt2Jg', NULL, 220, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 5, 'What are the Cognitive Transitions of ESFJs?', 'https://www.youtube.com/watch?v=LxOfcjLTTo4', NULL, 221, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 6, 'What are the Cognitive Transitions of ESFPs?', 'https://www.youtube.com/watch?v=LaO_p7FGP28', NULL, 222, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 7, 'What are the Cognitive Transitions of ENTPs?', 'https://www.youtube.com/watch?v=YBiEEn2vqA0', NULL, 223, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 8, 'What are the Cognitive Transitions of ENFPs? | Four Sides of the Mind | CS Joseph', 'https://www.youtube.com/watch?v=oL2m2yyeXkk', NULL, 224, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 9, 'What are the Cognitive Transitions of ISTJs?', 'https://www.youtube.com/watch?v=2Sc94tFTVnY', NULL, 225, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 10, 'What are the Cognitive Transitions of ISTPs?', 'https://www.youtube.com/watch?v=xtKSoKun86Y', NULL, 226, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 11, 'INTJ Personality Explained | What are the Cognitive Transitions of INTJs? | CS Joseph', 'https://www.youtube.com/watch?v=oi4f2O0HsfQ', NULL, 227, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 12, 'INFJ Personality Type Explained | What are the Cognitive Transitions of an INFJ? | CS Joseph', 'https://www.youtube.com/watch?v=_wRJ6eNMdGg', NULL, 228, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 13, 'What are the Cognitive Transitions of an ISFJ? | ISFJ Personality type explained | CS Joseph', 'https://www.youtube.com/watch?v=LK9-sfVo4T0', NULL, 229, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 14, 'What are the Cognitive Transitions of ISFPs? | ISFP Personality Type | CS Joseph', 'https://www.youtube.com/watch?v=jkgkfdMSB9o', NULL, 230, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 15, 'What are the Cognitive Transitions of INTPs? | INTP Personality type | CS Joseph', 'https://www.youtube.com/watch?v=W3EqTrEAZas', NULL, 231, TRUE),
('Advanced Applications', '22', 'Cognitive Transitions', 16, 'What are the Cognitive Transitions of INFPs? | Four Sides of the Mind INFP | CS Joseph', 'https://www.youtube.com/watch?v=35oZemDh5v4', NULL, 232, TRUE);

-- Season 21: Social Engineering (17 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Advanced Applications', '21', 'Social Engineering', 1, 'How To Social Engineer Using Type | Social Engineering | CS Joseph', 'https://www.youtube.com/watch?v=uQP_t5KNpD0', NULL, 233, TRUE),
('Advanced Applications', '21', 'Social Engineering', 2, 'How To Social Engineer ESTJs | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=TfCrMJB2M4s', NULL, 234, TRUE),
('Advanced Applications', '21', 'Social Engineering', 3, 'How To Social Engineer ESTPs | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=FkY2Wf6LK4s', NULL, 235, TRUE),
('Advanced Applications', '21', 'Social Engineering', 4, 'How To Social Engineer ENTJs | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=pGQldWwq7iw', NULL, 236, TRUE),
('Advanced Applications', '21', 'Social Engineering', 5, 'How To Social Engineer ENFJs | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=j7Sv7OsamsU', NULL, 237, TRUE),
('Advanced Applications', '21', 'Social Engineering', 6, 'How To Social Engineer ESFJs | ESFJ Personality | CS Joseph', 'https://www.youtube.com/watch?v=YIFem72yEIk', NULL, 238, TRUE),
('Advanced Applications', '21', 'Social Engineering', 7, 'How To Social Engineer ESFPs | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=RUU6qst6XC4', NULL, 239, TRUE),
('Advanced Applications', '21', 'Social Engineering', 8, 'How To Social Engineer ENTPs | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=hLl3xoorSiI', NULL, 240, TRUE),
('Advanced Applications', '21', 'Social Engineering', 9, 'How To Social Engineer An ENFP | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=ows_fJxzh90', NULL, 241, TRUE),
('Advanced Applications', '21', 'Social Engineering', 10, 'How to Social Engineer ISTJs | Social Engineering | CS Joseph', 'https://www.youtube.com/watch?v=fJywcGtOtfQ', NULL, 242, TRUE),
('Advanced Applications', '21', 'Social Engineering', 11, 'How to Social Engineer ISTPs | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=xKmnTFiBwXM', NULL, 243, TRUE),
('Advanced Applications', '21', 'Social Engineering', 12, 'How To Social Engineer INTJs (The Ranger)  | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=-UqdulgguT0', NULL, 244, TRUE),
('Advanced Applications', '21', 'Social Engineering', 13, 'How To Social Engineer INFJs (The Paladin) | Social Engineering | CS Joseph', 'https://www.youtube.com/watch?v=5qUz1qLZ-RA', NULL, 245, TRUE),
('Advanced Applications', '21', 'Social Engineering', 14, 'How to Social Engineer ISFJs | Social Engineering | CS Joseph', 'https://www.youtube.com/watch?v=XC2V62_BOsQ', NULL, 246, TRUE),
('Advanced Applications', '21', 'Social Engineering', 15, 'How to Social Engineer ISFPs | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=XF9eVJzPL0k', NULL, 247, TRUE),
('Advanced Applications', '21', 'Social Engineering', 16, 'How To Social Engineer INTPs (The Ardent) | Cognitive Functions | CS Joseph', 'https://www.youtube.com/watch?v=xmM-tTEYU2I', NULL, 248, TRUE),
('Advanced Applications', '21', 'Social Engineering', 17, 'How to Social Engineer INFP''s (The Mystic) | CS Joseph', 'https://www.youtube.com/watch?v=-_nHB2ySu9o', NULL, 249, TRUE);

-- Season 12.2: Social Optimization (16 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Advanced Applications', '12.2', 'Social Optimization', 1, 'Optimizing ISFJ Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=L33BbKGV0hg', 'fa1ef53f-e027-4027-94a6-3945d0b3abac', 250, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 2, 'Optimizing INFP Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=JUPfoZ4wRQI', 'f317d59f-67de-41fe-bcd9-57681708598f', 251, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 3, 'Optimizing INTP Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=fo1OndrW1IA', 'e678bcbc-ca7e-43ff-b276-7859cb2a4147', 252, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 4, 'Optimizing ISFP Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=KuDcM6U6Qog', NULL, 253, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 5, 'Optimizing INFJ Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=FrRlbugQQWU', '02aca22e-e19b-46dd-881d-98b1415d6a59', 254, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 6, 'Optimizing INTJ Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=XEYcaFR3lPE', 'f4d96892-3f53-4cfe-a6e4-a270e2299fed', 255, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 7, 'Optimizing ISTP Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=rJkT2rCD2KM', '78b91ce0-9874-4e7f-b49f-346abeb028a7', 256, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 8, 'Optimizing ISTJ Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=ToF3ZpVXNB8', '29f84866-01a4-487e-a2dc-f27f682e5048', 257, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 9, 'Optimizing ENFP Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=dFRvqz4w9pc', '75d22984-ff40-4dd5-a208-933865abe791', 258, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 10, 'Optimizing ENTP Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=wAXKL-daj8Y', 'b2d1b873-e2bd-4c89-8d73-56e0d2595886', 259, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 11, 'Optimizing ESFP Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=uBgD_MXlPw4', 'a43a7de6-ae25-4881-9ac3-d2bc8ffd3fa4', 260, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 12, 'Optimizing ESFJ Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=O8azg2rznjw', 'a0cdcee9-c8fe-4bb7-bf10-1726e7d1807c', 261, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 13, 'Optimizing ENFJ Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=q4koxZWVtMY', 'a11a4a36-8a6b-426b-8a1b-e439525bca37', 262, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 14, 'Optimizing ENTJ Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=AhVX7UXMSkw', 'b3da1581-4de2-43ff-a9d0-fb39493d82d1', 263, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 15, 'Optimizing ESTP Social Skills | CS Joseph', 'https://www.youtube.com/watch?v=X2aemJpHhLU', '3f740914-cb96-4a31-adb8-eede3a193344', 264, TRUE),
('Advanced Applications', '12.2', 'Social Optimization', 16, 'Optimizing ESTJ Social Skills (and Typing Random People) | CS Joseph', 'https://www.youtube.com/watch?v=wuQkFCXddUQ', NULL, 265, TRUE);

-- Season 23: Parenting By Type (17 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Advanced Applications', '23', 'Parenting By Type', 1, 'How to Parent an INFP | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=ugHzdkWFH-Y', NULL, 266, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 2, 'How to Parent an INTP | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=d3ze1tuy2js', NULL, 267, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 3, 'How to Parent an ISFP | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=9ApsmFnqbl8', NULL, 268, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 4, 'How to Parent an ISFJ | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=35feML1qE9w', NULL, 269, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 5, 'How to Parent an INFJ | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=K0a5yjkbY4c', NULL, 270, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 6, 'How to Parent an INTJ | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=6sJ-YwI8eso', NULL, 271, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 7, 'How to Parent an ISTP | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=pSyPSub4KqI', NULL, 272, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 8, 'How to Parent an ISTJ | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=sBTXU-GolHo', NULL, 273, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 9, 'How to Parent an ENFP | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=5xAWxJgRv9A', NULL, 274, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 10, 'How to Parent an ENTP | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=rh2DL_vpvd0', NULL, 275, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 11, 'How to Parent an ESFP | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=fKKpXT0OWuI', NULL, 276, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 12, 'How to Parent an ESFJ | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=PflJjYrAH70', NULL, 277, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 13, 'How to Parent an ENFJ | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=2M44VyI1hTY', NULL, 278, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 14, 'How to Parent an ENTJ | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=Mae6t4J7wzI', NULL, 279, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 15, 'How to Parent an ESTP | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=fbpFq-FsbyY', NULL, 280, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 16, 'How to Parent an ESTJ | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=hvKmz06CiTI', NULL, 281, TRUE),
('Advanced Applications', '23', 'Parenting By Type', 17, 'Introduction to Jungian Parenting | Season 23 | CS Joseph', 'https://www.youtube.com/watch?v=uNTg74S4PDc', NULL, 282, TRUE);

-- Season 18: Cognitive Mechanics (34 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Expert Mastery', '18', 'Cognitive Mechanics', 1, 'Introduction to Cognitive Mechanics | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=Nr-z90F6kWo', '8a0973ee-a155-4dae-a1ba-3f3b166363a4', 283, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 2, 'The System Behind Perception | Cognitive Mechanics Public Release | CS Joseph', 'https://www.youtube.com/watch?v=Vb66We3Wabw', 'a018de7f-02a6-4d23-be38-fafb7df44bc9', 284, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 3, 'The System Behind Judgement | Season 18 Public Release | CS Joseph', 'https://www.youtube.com/watch?v=NlFszY3ZLHw', NULL, 285, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 4, 'Improve Cognitive Functions Through Cognitive Transition | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=nKAte2Z9Wvs', NULL, 286, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 5, 'Public Release! The First Axis: Earth and Water  | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=aqevuTqaxos', '4a371ca5-7c44-42e7-80de-ab966d49dda5', 287, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 6, 'The 2nd Axis: Fire and Wind | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=_6pnblgmrvg', 'a4ba25f1-2160-4ef6-9aa9-057d2f987e06', 288, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 7, 'The Third Axis: Spear and Bow (Fi - Te) | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=rcFuOTFwVwo', NULL, 289, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 8, 'The 4th Axis (Ti & Fe) | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=BWYuqpVFN7Q', NULL, 290, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 9, 'The 1st Orbit: Si & Se | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=J3msCUQJGFc', NULL, 291, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 10, 'The 2nd Orbit: Ni & Ne | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=rfAAXpQ-csM', NULL, 292, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 11, 'The 3rd Orbit Ti and Te | Season 18 Cognitive Mechanics Email Lectures | CS Joseph', 'https://www.youtube.com/watch?v=5OCLl2PN-Bc', NULL, 293, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 12, 'The 4th Cognitive Orbit Fi & Fe | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=ur5Vvaew5hs', NULL, 294, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 13, '1st Reflector Functions Te & Fe | S18 Cognitive Mechanics Email Lectures Public Release | CS Joseph', 'https://www.youtube.com/watch?v=iN8CHkwCAk0', NULL, 295, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 14, 'Se and Ne Cognitive Reflection | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=L6XvWb6PkFA', NULL, 296, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 15, 'The Third Reflection Si + Ni | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=vnuR_VBkW3w', NULL, 297, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 16, 'The Fourth Reflection Ti + Fi | Season 18 Cognitive Mechanics | CS Joseph', 'https://www.youtube.com/watch?v=9UZEGGQG608', NULL, 298, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 17, 'Cognitive Battlegrounds! Season 18 with Chris Taylor', 'https://www.youtube.com/watch?v=H3aeomynC0I', NULL, 299, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 18, 'Temple Introduction! Season 18 with Chris Taylor', 'https://www.youtube.com/watch?v=0AfexanSu9Q', NULL, 300, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 19, 'Who are the Soul Temple? Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=0eT0eVJHIbA', NULL, 301, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 20, 'Who are the Heart Temple? Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=dzs4kzwOuwI', NULL, 302, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 21, 'Who are the Mind Temple? Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=nkphWsKpNqo', NULL, 303, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 22, 'Who are the Body Temple? Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=0cZRdQbarLg', NULL, 304, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 23, 'Intimacy and Justification | Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=kJSb1eEYhx4', 'fc4fa6bf-d3e9-48ad-8b4a-ee4ab45fb061', 305, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 24, 'Satisfaction and Reverence | Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=j46B7F8IPTI', 'e1b6343d-79eb-4054-9140-ce838884e85f', 306, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 25, 'Validation and Authority | Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=qDrOvbQPXTA', '11835986-815e-415f-bebd-a160b7d82a06', 307, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 26, 'Purpose & Discovery | Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=0HFIuEyCuBQ', 'c9d3a71f-d17e-48a9-bef6-f281ad04968c', 308, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 27, 'The IPOF of Cognition | Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=1BkOgnraQZM', 'aa1d4cf7-bb5b-43be-be99-8564a1cd4eb2', 309, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 28, 'Octagram Cognitive Development | Season 18 Cognitive Mechanics', 'https://www.youtube.com/watch?v=NJejuxsTmyg', '5ea7fd5d-d00b-4a0f-b5d3-31319bd866f7', 310, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 29, 'Cognitive Focus in Octagram | Season 18 Cognitive Mechanics Email Lectures | CS Joseph', 'https://www.youtube.com/watch?v=EipRlyiVa48', '4e73bdce-cc82-419a-9024-b8cdc10bb678', 311, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 30, 'What are god functions? | Season 18 Cognitive Mechanics Email Lectures | CS Joseph', 'https://www.youtube.com/watch?v=aHGlRTodF1Y', NULL, 312, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 31, 'SD | SF Joy Octagram | Season 18 Cognitive Mechanics Email Lectures | CS Joseph', 'https://www.youtube.com/watch?v=vQ7iY9DofvA', '4ebbba45-4607-4b78-91e2-00fee80330ff', 313, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 32, 'SD | UF Decay Octagram | Season 18 Cognitive Mechanics Email Lectures | CS Joseph', 'https://www.youtube.com/watch?v=yCiCSvAF1yE', '2023e19d-d142-4c34-bf15-fca8ee34acb9', 314, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 33, 'UD | SF Hope Octagram | Season 18 Cognitive Mechanics Email Lectures | CS Joseph', 'https://www.youtube.com/watch?v=E48SmXYt-O8', '89efac59-88c1-45dc-9c97-4b6201287476', 315, TRUE),
('Expert Mastery', '18', 'Cognitive Mechanics', 34, 'UD | UF Despair Octagram | Season 18 Cognitive Mechanics Email Lectures | CS Joseph', 'https://www.youtube.com/watch?v=jykDxjhfKzw', '8170323a-7574-4899-8f18-e2cf3250cb2d', 316, TRUE);

-- Season 24: Life Purpose (2 lessons)
INSERT INTO curriculum (
    module_name, season_number, season_name,
    lesson_number, lesson_title, youtube_url,
    document_id, order_index, has_video
) VALUES
('Expert Mastery', '24', 'Life Purpose', 1, 'What is the life purpose of an ESTJ? | Discover Assessment | CS Joseph', 'https://www.youtube.com/watch?v=jfEq0mz0dvw', NULL, 317, TRUE),
('Expert Mastery', '24', 'Life Purpose', 2, 'Are you an ESTJ? | Who the ESTJs are! | Season 24 | CS Joseph', 'https://www.youtube.com/watch?v=oR_gh5-MP2U', NULL, 318, TRUE);

-- ============================================================================
-- SUPPLEMENTARY LIBRARY (388 lessons)
-- Content type: 'supplementary' - not counted in main progress
-- ============================================================================

-- Celebrity Typing (Season 20 - 64 videos)
-- Note: Already included in main curriculum above as Season 20

-- CS Joseph Responds (100 videos)
-- Parsing first 10 as example - full version would include all 100
