from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User

HOME_URL = reverse('posts:index')
CREATE_URL = reverse('posts:post_create')
NOT_FOUND_URL = '/zzz/'
INDEX_HTML = 'posts/index.html'
GROUP_LIST_HTML = 'posts/group_list.html'
PROFILE_HTML = 'posts/profile.html'
POST_DETAIL_HTML = 'posts/post_detail.html'
POST_CREATE_HTML = 'posts/create_post.html'
NOT_FOUND_HTML = 'core/404.html'


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser1')
        cls.user2 = User.objects.create_user(username='testuser2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа'
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = PostsURLTests.user
        self.post = PostsURLTests.post
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user2 = PostsURLTests.user2
        self.not_author_client = Client()
        self.not_author_client.force_login(self.user2)

    def test_pages_urls_templates(self):
        group_list_url = reverse('posts:group_list', args=[self.group.slug])
        profile_url = reverse('posts:profile', args=[self.user])
        post_detail_url = reverse('posts:post_detail', args=[self.post.id])
        post_edit_url = reverse('posts:post_edit', args=[self.post.id])
        guest = self.guest_client
        auth = self.authorized_client
        not_auth = self.not_author_client
        urls_clients_status_templates = [
            [HOME_URL, guest, HTTPStatus.OK, INDEX_HTML],
            [group_list_url, guest, HTTPStatus.OK, GROUP_LIST_HTML],
            [profile_url, guest, HTTPStatus.OK, PROFILE_HTML],
            [post_detail_url, guest, HTTPStatus.OK, POST_DETAIL_HTML],
            [CREATE_URL, auth, HTTPStatus.OK, POST_CREATE_HTML],
            [post_edit_url, auth, HTTPStatus.OK, POST_CREATE_HTML],
            [post_edit_url, not_auth, HTTPStatus.FOUND, POST_CREATE_HTML],
            [NOT_FOUND_URL, auth, HTTPStatus.NOT_FOUND, NOT_FOUND_HTML]
        ]
        for url, client, status, template in urls_clients_status_templates:
            with self.subTest(url=url):
                response = client.get(url)
                if client == not_auth:
                    self.assertRedirects(response, post_detail_url)
                else:
                    self.assertEqual(response.status_code, status)
                    self.assertTemplateUsed(response, template)
