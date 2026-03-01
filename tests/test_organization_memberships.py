from pytest_clerk_mock import MockClerkClient


class TestOrganizationMembershipsCreate:
    """Tests for creating organization memberships."""

    def test_create_membership(self, mock_clerk: MockClerkClient) -> None:
        """Create membership returns membership with provided values."""

        membership = mock_clerk.organization_memberships.create(
            organization_id="org_123",
            user_id="user_456",
            role="org:member",
        )

        assert membership.id == "orgmem_org_123_user_456"
        assert membership.organization_id == "org_123"
        assert membership.user_id == "user_456"
        assert membership.role == "org:member"

    def test_create_membership_with_metadata(self, mock_clerk: MockClerkClient) -> None:
        """Create membership with metadata stores metadata correctly."""

        membership = mock_clerk.organization_memberships.create(
            organization_id="org_123",
            user_id="user_456",
            role="org:admin",
            public_metadata={"department": "engineering"},
            private_metadata={"salary_band": "L5"},
        )

        assert membership.public_metadata == {"department": "engineering"}
        assert membership.private_metadata == {"salary_band": "L5"}

    def test_create_membership_with_custom_role(self, mock_clerk: MockClerkClient) -> None:
        """Create membership with custom role."""

        membership = mock_clerk.organization_memberships.create(
            organization_id="org_123",
            user_id="user_456",
            role="org:billing_admin",
        )

        assert membership.role == "org:billing_admin"

    async def test_create_async(self, mock_clerk: MockClerkClient) -> None:
        """Async create works like sync version."""

        membership = await mock_clerk.organization_memberships.create_async(
            organization_id="org_async",
            user_id="user_async",
            role="org:member",
        )

        assert membership.id == "orgmem_org_async_user_async"
        assert membership.organization_id == "org_async"
        assert membership.user_id == "user_async"


class TestOrganizationMembershipsDelete:
    """Tests for deleting organization memberships."""

    def test_delete_membership(self, mock_clerk: MockClerkClient) -> None:
        """Delete removes membership and returns it."""

        mock_clerk.organization_memberships.create(
            organization_id="org_123",
            user_id="user_456",
            role="org:member",
        )

        deleted = mock_clerk.organization_memberships.delete(
            organization_id="org_123",
            user_id="user_456",
        )

        assert deleted is not None
        assert deleted.organization_id == "org_123"
        assert deleted.user_id == "user_456"

    def test_delete_nonexistent_returns_none(self, mock_clerk: MockClerkClient) -> None:
        """Delete nonexistent membership returns None."""

        result = mock_clerk.organization_memberships.delete(
            organization_id="org_nonexistent",
            user_id="user_nonexistent",
        )

        assert result is None

    async def test_delete_async(self, mock_clerk: MockClerkClient) -> None:
        """Async delete works like sync version."""

        await mock_clerk.organization_memberships.create_async(
            organization_id="org_async",
            user_id="user_async",
            role="org:member",
        )

        deleted = await mock_clerk.organization_memberships.delete_async(
            organization_id="org_async",
            user_id="user_async",
        )

        assert deleted is not None
        assert deleted.organization_id == "org_async"


class TestOrganizationMembershipsList:
    """Tests for listing organization memberships."""

    def test_list_filters_by_organization_and_user(
        self,
        mock_clerk: MockClerkClient,
    ) -> None:
        """List returns memberships matching organization and user filters."""

        mock_clerk.organization_memberships.create(
            organization_id="org_1",
            user_id="user_1",
            role="org:member",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_1",
            user_id="user_2",
            role="org:admin",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_2",
            user_id="user_1",
            role="org:member",
        )

        memberships = mock_clerk.organization_memberships.list(
            organization_id="org_1",
            user_id=["user_2"],
            limit=10,
            offset=0,
        )

        assert memberships.total_count == 1
        assert len(memberships.data) == 1
        assert memberships.data[0].organization_id == "org_1"
        assert memberships.data[0].user_id == "user_2"
        assert memberships.data[0].role == "org:admin"

    def test_list_applies_pagination(self, mock_clerk: MockClerkClient) -> None:
        """List applies offset and limit while preserving total_count."""

        mock_clerk.organization_memberships.create(
            organization_id="org_page",
            user_id="user_1",
            role="org:member",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_page",
            user_id="user_2",
            role="org:member",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_page",
            user_id="user_3",
            role="org:member",
        )

        memberships = mock_clerk.organization_memberships.list(
            organization_id="org_page",
            limit=1,
            offset=1,
        )

        assert memberships.total_count == 3
        assert len(memberships.data) == 1
        assert memberships.data[0].organization_id == "org_page"
        assert memberships.data[0].user_id == "user_2"

    def test_list_supports_user_id_include_exclude(
        self,
        mock_clerk: MockClerkClient,
    ) -> None:
        """List supports include and exclude semantics for user_id."""

        mock_clerk.organization_memberships.create(
            organization_id="org_filter",
            user_id="user_1",
            role="org:member",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_filter",
            user_id="user_2",
            role="org:member",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_filter",
            user_id="user_3",
            role="org:member",
        )

        memberships = mock_clerk.organization_memberships.list(
            organization_id="org_filter",
            user_id=["+user_1", "+user_2", "-user_2"],
            limit=10,
            offset=0,
        )

        assert memberships.total_count == 1
        assert len(memberships.data) == 1
        assert memberships.data[0].user_id == "user_1"

    def test_list_filters_by_role(self, mock_clerk: MockClerkClient) -> None:
        """List supports filtering by role."""

        mock_clerk.organization_memberships.create(
            organization_id="org_roles",
            user_id="user_1",
            role="org:member",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_roles",
            user_id="user_2",
            role="org:admin",
        )

        memberships = mock_clerk.organization_memberships.list(
            organization_id="org_roles",
            role=["org:admin"],
            limit=10,
            offset=0,
        )

        assert memberships.total_count == 1
        assert len(memberships.data) == 1
        assert memberships.data[0].user_id == "user_2"
        assert memberships.data[0].role == "org:admin"

    async def test_list_async(self, mock_clerk: MockClerkClient) -> None:
        """Async list returns memberships matching filters."""

        await mock_clerk.organization_memberships.create_async(
            organization_id="org_async",
            user_id="user_1",
            role="org:member",
        )
        await mock_clerk.organization_memberships.create_async(
            organization_id="org_async",
            user_id="user_2",
            role="org:admin",
        )
        await mock_clerk.organization_memberships.create_async(
            organization_id="org_other",
            user_id="user_1",
            role="org:member",
        )

        memberships = await mock_clerk.organization_memberships.list_async(
            organization_id="org_async",
            user_id=["user_1"],
            limit=1,
            offset=0,
        )

        assert memberships.total_count == 1
        assert len(memberships.data) == 1
        assert memberships.data[0].organization_id == "org_async"
        assert memberships.data[0].user_id == "user_1"

    async def test_list_async_accepts_extended_clerk_parameters(
        self,
        mock_clerk: MockClerkClient,
    ) -> None:
        """Async list accepts Clerk SDK optional parameters without failing."""

        await mock_clerk.organization_memberships.create_async(
            organization_id="org_extended",
            user_id="user_a",
            role="org:member",
        )
        await mock_clerk.organization_memberships.create_async(
            organization_id="org_extended",
            user_id="user_b",
            role="org:admin",
        )

        memberships = await mock_clerk.organization_memberships.list_async(
            organization_id="org_extended",
            order_by="-created_at",
            user_id=["user_a", "user_b"],
            email_address=["hello@example.com"],
            phone_number=["+15551234567"],
            username=["cool_user"],
            web3_wallet=["0xabc"],
            role=["org:member", "org:admin"],
            query="user",
            email_address_query="hello",
            phone_number_query="555",
            username_query="cool",
            name_query="hello",
            last_active_at_before=9_999_999_999_999,
            last_active_at_after=0,
            created_at_before=9_999_999_999_999,
            created_at_after=0,
            limit=10,
            offset=0,
            retries=None,
            server_url="https://api.clerk.test",
            timeout_ms=3_000,
            http_headers={"x-test-header": "1"},
        )

        assert memberships.total_count == 0
        assert memberships.data == []


class TestOrganizationMembershipsReset:
    """Tests for resetting organization memberships."""

    def test_reset_clears_memberships(self, mock_clerk: MockClerkClient) -> None:
        """Reset removes all memberships."""

        mock_clerk.organization_memberships.create(
            organization_id="org_1",
            user_id="user_1",
            role="org:member",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_2",
            user_id="user_2",
            role="org:admin",
        )

        mock_clerk.organization_memberships.reset()

        result1 = mock_clerk.organization_memberships.delete(
            organization_id="org_1",
            user_id="user_1",
        )
        result2 = mock_clerk.organization_memberships.delete(
            organization_id="org_2",
            user_id="user_2",
        )

        assert result1 is None
        assert result2 is None


class TestFixtureIsolation:
    """Tests that fixture resets between tests."""

    def test_fixture_isolation_first(self, mock_clerk: MockClerkClient) -> None:
        """First test creates a membership."""

        mock_clerk.organization_memberships.create(
            organization_id="org_isolation",
            user_id="user_isolation",
            role="org:member",
        )

        deleted = mock_clerk.organization_memberships.delete(
            organization_id="org_isolation",
            user_id="user_isolation",
        )

        assert deleted is not None

    def test_fixture_isolation_second(self, mock_clerk: MockClerkClient) -> None:
        """Second test sees empty store."""

        result = mock_clerk.organization_memberships.delete(
            organization_id="org_isolation",
            user_id="user_isolation",
        )

        assert result is None
