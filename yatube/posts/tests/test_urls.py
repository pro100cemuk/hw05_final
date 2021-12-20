from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Follow, Group, Post, User

HOME_URL = reverse('posts:index')
CREATE_URL = reverse('posts:post_create')
FOLLOW_INDEX_URL = reverse('posts:follow_index')
NOT_FOUND_URL = '/zzz/'
INDEX_HTML = 'posts/index.html'
GROUP_LIST_HTML = 'posts/group_list.html'
PROFILE_HTML = 'posts/profile.html'
POST_DETAIL_HTML = 'posts/post_detail.html'
POST_CREATE_HTML = 'posts/create_post.html'
FOLLOW_INDEX_HTML = 'posts/follow.html'
NOT_FOUND_HTML = 'core/404.html'


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser1')
        cls.user2 = User.objects.create_user(username='testuser2')
        cls.user3 = User.objects.create_user(username='testuser3')
        cls.user4 = User.objects.create_user(username='testuser4')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа'
        )
        Follow.objects.create(user=cls.user4, author=cls.user)

    def setUp(self):
        self.guest_client = Client()
        self.user = PostsURLTests.user
        self.post = PostsURLTests.post
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user2 = PostsURLTests.user2
        self.not_author_client = Client()
        self.not_author_client.force_login(self.user2)
        self.user3 = PostsURLTests.user3
        self.follower = Client()
        self.follower.force_login(self.user3)
        self.user4 = PostsURLTests.user4
        self.unfollow = Client()
        self.unfollow.force_login(self.user4)

    def test_pages_urls_templates(self):
        group_list_url = reverse('posts:group_list', args=[self.group.slug])
        profile_url = reverse('posts:profile', args=[self.user])
        post_detail_url = reverse('posts:post_detail', args=[self.post.id])
        post_edit_url = reverse('posts:post_edit', args=[self.post.id])
        add_comment_url = reverse('posts:add_comment', args=[self.post.id])
        follow_url = reverse('posts:profile_follow', args=[self.user])
        unfollow_url = reverse('posts:profile_unfollow', args=[self.user])
        guest = self.guest_client
        auth = self.authorized_client
        not_auth = self.not_author_client
        follower = self.follower
        unfollower = self.unfollow
        urls_clients_status_templates = [
            [HOME_URL, guest, HTTPStatus.OK, INDEX_HTML],
            [group_list_url, guest, HTTPStatus.OK, GROUP_LIST_HTML],
            [profile_url, guest, HTTPStatus.OK, PROFILE_HTML],
            [post_detail_url, guest, HTTPStatus.OK, POST_DETAIL_HTML],
            [CREATE_URL, auth, HTTPStatus.OK, POST_CREATE_HTML],
            [post_edit_url, auth, HTTPStatus.OK, POST_CREATE_HTML],
            [post_edit_url, not_auth, HTTPStatus.FOUND, POST_DETAIL_HTML],
            [NOT_FOUND_URL, auth, HTTPStatus.NOT_FOUND, NOT_FOUND_HTML],
            [add_comment_url, not_auth, HTTPStatus.OK, POST_DETAIL_HTML],
            [FOLLOW_INDEX_URL, auth, HTTPStatus.OK, FOLLOW_INDEX_HTML],
            [follow_url, follower, HTTPStatus.OK, PROFILE_HTML],
            [unfollow_url, unfollower, HTTPStatus.OK, PROFILE_HTML],
        ]
        for url, client, status, template in urls_clients_status_templates:
            with self.subTest(url=url):
                response = client.get(url)
                if client == not_auth:
                    self.assertRedirects(response, post_detail_url)
                elif client == (follower or unfollower):
                    self.assertRedirects(response, profile_url)
                elif client == (guest or auth):
                    self.assertEqual(response.status_code, status)
                    self.assertTemplateUsed(response, template)
