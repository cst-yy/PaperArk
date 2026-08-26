import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import DuplicateTagError, InvalidFolderError, InvalidTagError, KeywordNotFoundError, PaperNotFoundError
from app.models import Document, Folder, Keyword, Paper, PaperAuthor, PaperFolder, PaperKeyword, Tag, User
from app.schemas.keyword import KeywordInput, KeywordReplacement
from app.schemas.paper import AuthorBrief, PaperMetadataReplaceRequest
from app.schemas.tag import TagCreate, TagUpdate
from app.services.paper_service import PaperMapper, PaperService
from app.services.keyword_service import KeywordService
from app.services.tag_service import TagService


async def create_user(session, suffix: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    session.add(User(id=user_id, username=f"user-{suffix}", email=f"{suffix}@example.com", password_hash=""))
    await session.flush()
    return user_id


@pytest.mark.asyncio
async def test_paper_detail_eager_loads_complete_document_brief(session):
    user_id = await create_user(session, "detail-document")
    paper = Paper(user_id=user_id, title="Reader detail", status="ready")
    session.add(paper)
    await session.flush()
    document = Document(
        paper_id=paper.id,
        file_path="pdfs/reader-detail.pdf",
        original_filename="reader-detail.pdf",
        file_size=1234,
        mime_type="application/pdf",
        parse_status="ready",
        parser_version="test-parser",
    )
    session.add(document)
    await session.commit()

    response = PaperMapper.to_detail_response(
        await PaperService(session).get_paper(user_id, paper.id)
    )

    assert response.document is not None
    assert response.document.id == document.id
    assert response.document.original_filename == "reader-detail.pdf"
    assert response.document.file_size == 1234
    assert response.document.parser_version == "test-parser"


@pytest.mark.asyncio
async def test_tag_normalized_duplicate_and_rename_duplicate(session):
    user_id = await create_user(session, "tag-owner")
    service = TagService(session)
    first = await service.create_tag(user_id, TagCreate(name="  Federated Learning  "))

    assert first.name == "Federated Learning"
    with pytest.raises(DuplicateTagError):
        await service.create_tag(user_id, TagCreate(name="federated learning"))

    other = await service.create_tag(user_id, TagCreate(name="Privacy"))
    with pytest.raises(DuplicateTagError):
        await service.update_tag(user_id, other.id, TagUpdate(name="FEDERATED LEARNING"))


@pytest.mark.asyncio
async def test_keyword_delete_is_owner_scoped_and_removes_paper_links(session):
    owner_id = await create_user(session, "keyword-delete-owner")
    other_id = await create_user(session, "keyword-delete-other")
    paper = Paper(user_id=owner_id, title="Keyword cleanup")
    session.add(paper)
    await session.flush()
    service = KeywordService(session)
    keyword = await service.get_or_create(owner_id, KeywordInput(name="Malformed keyword"))
    session.add(PaperKeyword(paper_id=paper.id, keyword_id=keyword.id, source="metadata"))
    await session.flush()

    with pytest.raises(KeywordNotFoundError):
        await service.delete_keyword(other_id, keyword.id)

    await service.delete_keyword(owner_id, keyword.id)
    await session.flush()

    assert await session.get(Keyword, keyword.id) is None
    links = (await session.execute(select(PaperKeyword).where(PaperKeyword.keyword_id == keyword.id))).scalars().all()
    assert links == []


@pytest.mark.asyncio
async def test_paper_tag_and_folder_replacement_rejects_foreign_objects(session):
    owner_id = await create_user(session, "owner")
    other_id = await create_user(session, "other")
    paper = Paper(id=uuid.uuid4(), user_id=owner_id, title="Owner paper")
    own_tag = Tag(id=uuid.uuid4(), user_id=owner_id, name="Own", normalized_name="own")
    own_folder = Folder(id=uuid.uuid4(), user_id=owner_id, name="Own folder")
    foreign_tag = Tag(id=uuid.uuid4(), user_id=other_id, name="Foreign", normalized_name="foreign")
    foreign_folder = Folder(id=uuid.uuid4(), user_id=other_id, name="Foreign folder")
    session.add_all([paper, own_tag, own_folder, foreign_tag, foreign_folder])
    await session.flush()
    service = PaperService(session)

    replaced = await service.replace_tags(owner_id, paper.id, [own_tag.id])
    assert [item.tag_id for item in replaced.tags] == [own_tag.id]
    with pytest.raises(InvalidTagError):
        await service.replace_tags(owner_id, paper.id, [foreign_tag.id])
    await service.replace_folders(owner_id, paper.id, [own_folder.id])
    folder_ids = (await session.execute(select(PaperFolder.folder_id).where(PaperFolder.paper_id == paper.id))).scalars().all()
    assert folder_ids == [own_folder.id]
    with pytest.raises(InvalidFolderError):
        await service.replace_folders(owner_id, paper.id, [foreign_folder.id])
    with pytest.raises(PaperNotFoundError):
        await service.replace_tags(other_id, paper.id, [foreign_tag.id])


@pytest.mark.asyncio
async def test_author_replacement_resets_order_reuses_orcid_and_preserves_same_name_affiliation(session):
    user_id = await create_user(session, "authors")
    paper = Paper(id=uuid.uuid4(), user_id=user_id, title="Author paper")
    session.add(paper)
    await session.flush()
    service = PaperService(session)

    first = await service.replace_authors(user_id, paper.id, [
        AuthorBrief(name="Wei Wang", affiliation="PKU", author_order=99),
        AuthorBrief(name="Wei Wang", affiliation="MIT", author_order=0),
        AuthorBrief(name="Ada Lovelace", orcid="https://orcid.org/0000-0002-1825-0097"),
    ])
    assert [item.author_order for item in first.authors] == [0, 1, 2]
    assert [item.author.affiliation for item in first.authors[:2]] == ["PKU", "MIT"]
    orcid_author_id = first.authors[2].author.id

    second = await service.replace_authors(user_id, paper.id, [
        AuthorBrief(name="Ada Lovelace", orcid="0000-0002-1825-0097"),
        AuthorBrief(name="Wei Wang", affiliation="MIT"),
    ])
    assert [item.author_order for item in second.authors] == [0, 1]
    assert second.authors[0].author.id == orcid_author_id
    assert second.authors[1].author.affiliation == "MIT"


@pytest.mark.asyncio
async def test_author_replacement_rolls_back_links_when_replacement_fails(session):
    user_id = await create_user(session, "author-rollback")
    paper = Paper(id=uuid.uuid4(), user_id=user_id, title="Rollback paper")
    session.add(paper)
    await session.flush()
    service = PaperService(session)
    await service.replace_authors(user_id, paper.id, [AuthorBrief(name="Stable Author")])

    original_link = await session.scalar(select(PaperAuthor).where(PaperAuthor.paper_id == paper.id))
    assert original_link is not None

    original_link_author = service._link_authors

    async def fail_after_link(paper_id, authors):
        await original_link_author(paper_id, authors)
        raise RuntimeError("simulated replacement failure")

    service._link_authors = fail_after_link
    with pytest.raises(RuntimeError, match="simulated replacement failure"):
        await service.replace_authors(user_id, paper.id, [AuthorBrief(name="New Author")])

    links = (await session.execute(select(PaperAuthor).where(PaperAuthor.paper_id == paper.id))).scalars().all()
    assert [link.author_id for link in links] == [original_link.author_id]


@pytest.mark.asyncio
async def test_keyword_replacement_normalizes_deduplicates_and_preserves_non_manual_sources(session):
    user_id = await create_user(session, "keywords")
    paper = Paper(id=uuid.uuid4(), user_id=user_id, title="Keyword paper")
    session.add(paper)
    await session.flush()
    service = PaperService(session)

    result = await service.replace_keywords(user_id, paper.id, KeywordReplacement(keywords=[
        KeywordInput(name=" Federated Learning "),
        KeywordInput(name="federated learning"),
        KeywordInput(name="Non-IID"),
    ]))
    assert [keyword.display_name for keyword in PaperMapper.to_detail_response(result).keywords] == ["Federated Learning", "Non-IID"]
    keywords = (await session.execute(select(Keyword).where(Keyword.user_id == user_id))).scalars().all()
    assert len(keywords) == 2

    federated = next(item for item in keywords if item.normalized_name == "federated learning")
    session.add(PaperKeyword(paper_id=paper.id, keyword_id=federated.id, source="metadata"))
    await session.flush()
    result = await service.replace_keywords(user_id, paper.id, KeywordReplacement(keywords=[]))
    federated_result = next(
        item for item in PaperMapper.to_detail_response(result).keywords if item.id == federated.id
    )
    assert federated_result.sources == ["metadata"]


@pytest.mark.asyncio
async def test_keyword_replacement_rolls_back_when_keyword_creation_fails(session):
    user_id = await create_user(session, "keyword-rollback")
    paper = Paper(id=uuid.uuid4(), user_id=user_id, title="Keyword rollback")
    session.add(paper)
    await session.flush()
    service = PaperService(session)
    await service.replace_keywords(user_id, paper.id, KeywordReplacement(keywords=[KeywordInput(name="Stable")]))

    original_get_or_create = service.replace_keywords.__globals__["KeywordService"].get_or_create

    async def fail_after_create(keyword_service, owner_id, item):
        await original_get_or_create(keyword_service, owner_id, item)
        raise RuntimeError("simulated keyword replacement failure")

    service.replace_keywords.__globals__["KeywordService"].get_or_create = fail_after_create
    try:
        with pytest.raises(RuntimeError, match="simulated keyword replacement failure"):
            await service.replace_keywords(user_id, paper.id, KeywordReplacement(keywords=[KeywordInput(name="Replacement")]))
    finally:
        service.replace_keywords.__globals__["KeywordService"].get_or_create = original_get_or_create

    linked_keyword_names = (await session.execute(
        select(Keyword.display_name)
        .join(PaperKeyword, PaperKeyword.keyword_id == Keyword.id)
        .where(PaperKeyword.paper_id == paper.id)
    )).scalars().all()
    assert linked_keyword_names == ["Stable"]


@pytest.mark.asyncio
async def test_metadata_aggregate_replaces_all_editor_fields_atomically(session):
    user_id = await create_user(session, "aggregate")
    paper = Paper(id=uuid.uuid4(), user_id=user_id, title="Original")
    tag = Tag(id=uuid.uuid4(), user_id=user_id, name="Research", normalized_name="research")
    folder = Folder(id=uuid.uuid4(), user_id=user_id, name="Reading")
    session.add_all([paper, tag, folder])
    await session.flush()

    result = await PaperService(session).replace_metadata_aggregate(
        user_id,
        paper.id,
        PaperMetadataReplaceRequest(
            title="Updated", abstract="Abstract", doi="10.1000/UPDATED",
            publication_year=2025, citation_count=42,
            authors=[AuthorBrief(name="Alice", affiliation="University A")],
            tag_ids=[tag.id], folder_ids=[folder.id],
            keywords=[KeywordInput(name="Federated Learning")],
        ),
    )
    response = PaperMapper.to_detail_response(result)
    assert response.title == "Updated"
    assert [author.name for author in response.authors] == ["Alice"]
    assert [item.id for item in response.tags] == [tag.id]
    assert [item.id for item in response.folders] == [folder.id]
    assert [item.display_name for item in response.keywords] == ["Federated Learning"]


@pytest.mark.asyncio
async def test_metadata_aggregate_rolls_back_every_field_for_foreign_tag(session):
    owner_id = await create_user(session, "aggregate-owner")
    other_id = await create_user(session, "aggregate-other")
    paper = Paper(id=uuid.uuid4(), user_id=owner_id, title="Original")
    own_tag = Tag(id=uuid.uuid4(), user_id=owner_id, name="Stable tag", normalized_name="stable tag")
    foreign_tag = Tag(id=uuid.uuid4(), user_id=other_id, name="Foreign", normalized_name="foreign")
    folder = Folder(id=uuid.uuid4(), user_id=owner_id, name="Stable folder")
    session.add_all([paper, own_tag, foreign_tag, folder])
    await session.flush()
    service = PaperService(session)
    await service.replace_metadata_aggregate(
        owner_id, paper.id,
        PaperMetadataReplaceRequest(
            title="Original", authors=[AuthorBrief(name="Original Author")],
            tag_ids=[own_tag.id], folder_ids=[folder.id], keywords=[KeywordInput(name="Stable")],
        ),
    )

    with pytest.raises(InvalidTagError):
        await service.replace_metadata_aggregate(
            owner_id, paper.id,
            PaperMetadataReplaceRequest(
                title="Should not persist", authors=[AuthorBrief(name="Replacement Author")],
                tag_ids=[foreign_tag.id], folder_ids=[], keywords=[KeywordInput(name="Replacement")],
            ),
        )

    restored = PaperMapper.to_detail_response(await service.get_paper(owner_id, paper.id))
    assert restored.title == "Original"
    assert [author.name for author in restored.authors] == ["Original Author"]
    assert [item.id for item in restored.tags] == [own_tag.id]
    assert [item.id for item in restored.folders] == [folder.id]
    assert [item.display_name for item in restored.keywords] == ["Stable"]


@pytest.mark.asyncio
async def test_metadata_aggregate_duplicate_doi_leaves_existing_aggregate_unchanged(session):
    user_id = await create_user(session, "aggregate-doi")
    existing = Paper(id=uuid.uuid4(), user_id=user_id, title="Existing", doi="10.1000/taken")
    paper = Paper(id=uuid.uuid4(), user_id=user_id, title="Original")
    session.add_all([existing, paper])
    await session.flush()
    service = PaperService(session)
    with pytest.raises(Exception, match="same identifier"):
        await service.replace_metadata_aggregate(
            user_id, paper.id,
            PaperMetadataReplaceRequest(
                title="Changed", doi="10.1000/taken", authors=[AuthorBrief(name="New")],
                keywords=[KeywordInput(name="New Keyword")],
            ),
        )
    response = PaperMapper.to_detail_response(await service.get_paper(user_id, paper.id))
    assert response.title == "Original"
    assert response.authors == []
    assert response.keywords == []
