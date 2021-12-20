import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.app_settings import POSTS_PER_PAGE
from posts.models import Comment, Follow, Group, Post, User

HOME_URL = reverse('posts:index')
CREATE_URL = reverse('posts:post_create')
FOLLOW_INDEX_URL = reverse('posts:follow_index')
INDEX_HTML = 'posts/index.html'
GROUP_LIST_HTML = 'posts/group_list.html'
PROFILE_HTML = 'posts/profile.html'
POST_DETAIL_HTML = 'posts/post_detail.html'
POST_CREATE_HTML = 'posts/create_post.html'
USERNAME = 'testuser'
PASSWORD = 'testpassword'
GROUP_TITLE = 'Тестовая группа'
GROUP_SLUG = 'test-slug'
TEXT_POST = 'Тестовый пост'
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.user2 = User.objects.create_user(username=USERNAME + '2')
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
        )
        cls.group2 = Group.objects.create(
            title=GROUP_TITLE + '2',
            slug=GROUP_SLUG + '2',
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=TEXT_POST,
            group=cls.group,
            image=cls.uploaded
        )
        cls.follower = User.objects.create_user(username=USERNAME + '3')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.unsubscribed_client = Client()
        self.unsubscribed_client.force_login(self.user2)
        self.following_client = Client()
        self.following_client.force_login(self.follower)
        self.group_list = reverse('posts:group_list', args=[self.group.slug])
        self.profile = reverse('posts:profile', args=[self.user])
        self.post_detail = reverse('posts:post_detail', args=[self.post.id])
        self.post_edit = reverse('posts:post_edit', args=[self.post.id])
        self.add_comment = reverse('posts:add_comment', args=[self.post.id])
        self.comments_count = Comment.objects.count()
        self.follow = reverse('posts:profile_follow', args=[self.follower])
        self.unfollow = reverse('posts:profile_unfollow', args=[self.follower])

    def test_pages_uses_correct_template(self):
        urls_templates = {
            HOME_URL: INDEX_HTML,
            self.group_list: GROUP_LIST_HTML,
            self.profile: PROFILE_HTML,
            self.post_detail: POST_DETAIL_HTML,
            CREATE_URL: POST_CREATE_HTML,
            self.post_edit: POST_CREATE_HTML,
        }
        cache.clear()
        for reverse_name, template in urls_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_correct_context_non_form_pages(self):
        reverse_names = [
            HOME_URL,
            self.group_list,
            self.profile,
            self.post_detail,
        ]
        cache.clear()
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                if reverse_name == self.post_detail:
                    test = response.context.get('post')
                else:
                    test = (
                        response.context['page_obj'].paginator.object_list
                        .order_by('-id')[0]
                    )
                self.assertEqual(test.text, self.post.text)
                self.assertEqual(test.author.id, self.post.author.id)
                self.assertEqual(test.group.id, self.post.group.id)
                self.assertEqual(test.id, self.post.id)
                self.assertEqual(test.image.name, self.post.image.name)

    def test_create_post_show_correct_context(self):
        uploaded2 = SimpleUploadedFile(
            name='small2.gif',
            content=SMALL_GIF,
            content_type='image/gif',
        )
        data = {
            'text': 'Новый тестовый текст',
            'group': self.group.id,
            'image': uploaded2,
        }
        response = self.authorized_client.post(CREATE_URL, data=data,
                                               follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.post.refresh_from_db()
        reverse_names = [
            HOME_URL,
            self.profile,
            self.group_list
        ]
        cache.clear()
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                test_post = (
                    response.context['page_obj'].paginator.object_list
                    .order_by('-id')[0]
                )
                self.assertEqual(test_post.text, data['text'])
                self.assertEqual(test_post.group.id, data['group'])
                self.assertEqual(
                    test_post.image.name, 'posts/' + data['image'].name
                )

    def test_edit_post_show_correct_context(self):
        uploaded3 = SimpleUploadedFile(
            name='small3.gif',
            content=SMALL_GIF,
            content_type='image/gif',
        )
        response = self.authorized_client.get(self.post_edit)
        form = response.context['form']
        data = form.initial
        data['text'] = 'Измененный тестовый текст'
        data['group'] = self.group2.id
        data['image'] = uploaded3
        response = self.authorized_client.post(
            self.post_edit, data=data, follow=True
        )
        self.post.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(data['text'], self.post.text)
        self.assertEqual(data['group'], self.post.group.id)
        self.assertEqual(
            self.post.image.name, 'posts/' + data['image'].name
        )

    def test_create_comments_show_correct_context(self):
        data = {
            'text': 'Тестовый коммент'
        }
        response = self.authorized_client.post(
            self.add_comment,
            data=data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        comments_count_after = Comment.objects.count()
        self.assertEqual(comments_count_after, self.comments_count + 1)
        response = self.authorized_client.get(self.post_detail)
        test_comment = (
            response.context['comments'][0]
        )
        self.assertEqual(test_comment.text, data['text'])

    def test_cache(self):
        cache.clear()
        bd_posts_before = Post.objects.count()
        new_post = Post.objects.create(
            author=self.user,
            text='cache_test',
            group=self.group
        )
        response = self.authorized_client.get(HOME_URL)
        new_post_context = (
            response.context['page_obj'].paginator.object_list
            .order_by('-id')[0]
        )
        self.assertEqual(new_post_context.text, 'cache_test')
        self.assertEqual(new_post_context.author, self.user)
        self.assertEqual(new_post_context.group.id, self.group.id)
        bd_posts_count = Post.objects.count()
        self.assertEqual(bd_posts_before + 1, bd_posts_count)
        page_cached = response.content
        new_post.delete()
        bd_posts_after = Post.objects.count()
        self.assertEqual(bd_posts_before, bd_posts_after)
        response = self.authorized_client.get(HOME_URL)
        self.assertEqual(page_cached, response.content)
        cache.clear()
        response = self.authorized_client.get(HOME_URL)
        self.assertNotEqual(page_cached, response.content)

    def test_authorized_client_can_follow(self):
        self.authorized_client.post(self.follow, data=None, follow=True)
        self.assertIs(
            Follow.objects.filter(
                user=self.user,
                author=self.follower
            ).exists(),
            True)

    def test_authorized_client_can_unfollow(self):
        Follow.objects.create(user=self.user, author=self.follower)
        self.authorized_client.post(self.unfollow, data=None, follow=True)
        self.assertIs(
            Follow.objects.filter(
                user=self.user,
                author=self.follower
            ).exists(),
            False)

    def test_new_post_appears_in_sub_newsline(self):
        post = Post.objects.create(author=self.follower,
                                   text=TEXT_POST + 'follow')
        Follow.objects.create(user=self.user, author=self.follower)
        response = self.authorized_client.get(FOLLOW_INDEX_URL)
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_new_post_does_not_appear_in_unsub_newsline(self):
        post = Post.objects.create(author=self.follower,
                                   text=TEXT_POST + 'follow2')
        response = self.unsubscribed_client.get(FOLLOW_INDEX_URL)
        self.assertNotIn(post, response.context['page_obj'].object_list)


class TestPaginator(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username=USERNAME)
        self.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
        )
        self.post = Post.objects.bulk_create(
            [Post(text=f'{TEXT_POST}{i}', author=self.user, group=self.group)
             for i in range(14)]
        )
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group_list = reverse('posts:group_list', args=[self.group.slug])
        self.profile = reverse('posts:profile', args=[self.user])

    def test_paginator(self):
        reverse_names_templates = {
            HOME_URL: INDEX_HTML,
            self.group_list: GROUP_LIST_HTML,
            self.profile: PROFILE_HTML,
        }
        cache.clear()
        for reverse_name, template in reverse_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                length_p1 = len(response.context['page_obj'])
                self.assertEqual(length_p1, POSTS_PER_PAGE)
                response = self.authorized_client.get(reverse_name + '?page=2')
                length_p2 = len(response.context['page_obj'])
                remains = ((length_p1 + length_p2) - POSTS_PER_PAGE)
                self.assertEqual(length_p2, remains)
