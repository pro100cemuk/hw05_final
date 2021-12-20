import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post, User

HOME_URL = reverse('posts:index')
CREATE_URL = reverse('posts:post_create')
LOGIN_URL = reverse('users:login')
USERNAME = 'testuser'
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
class PostsFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=TEXT_POST,
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = PostsFormsTests.user
        self.post = PostsFormsTests.post
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = PostsFormsTests.group
        self.post_edit = reverse('posts:post_edit', args=[self.post.id])
        self.posts_count = Post.objects.count()
        self.redirected = f'{LOGIN_URL}?next={CREATE_URL}'

    def test_valid_form_create_post_in_db(self):
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif',
        )
        form_data = {
            'text': f'{TEXT_POST}2',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            CREATE_URL, data=form_data, follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.post.refresh_from_db()
        num_posts_after = Post.objects.count()
        self.posts_count += 1
        test = Post.objects.latest('id')
        self.assertEqual(test.text, form_data['text'])
        self.assertEqual(test.group.id, form_data['group'])
        self.assertEqual(test.author.id, self.user.id)
        self.assertEqual(test.image.name, 'posts/' + form_data['image'].name)
        self.assertEqual(self.posts_count, num_posts_after)

    def test_valid_form_change_post_in_db(self):
        uploaded = SimpleUploadedFile(
            name='small2.gif',
            content=SMALL_GIF,
            content_type='image/gif',
        )
        response = self.authorized_client.get(self.post_edit)
        form = response.context['form']
        form_data = form.initial
        form_data['text'] = f'Измененный {TEXT_POST}'
        form_data['group'] = self.group.id
        form_data['image'] = uploaded
        response = self.authorized_client.post(
            self.post_edit, data=form_data, follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.post.refresh_from_db()
        num_posts_after = Post.objects.count()
        test = Post.objects.latest('id')
        self.assertEqual(test.text, form_data['text'])
        self.assertEqual(test.group.id, form_data['group'])
        self.assertEqual(test.image.name, 'posts/' + form_data['image'].name)
        self.assertEqual(test.author.id, self.user.id)
        self.assertEqual(self.posts_count, num_posts_after)

    def test_unauthorized_client_cannot_create_post(self):
        form_data = {
            'text': f'{TEXT_POST}3',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            CREATE_URL, data=form_data, follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, self.redirected)
        num_posts_after = Post.objects.count()
        self.assertEqual(self.posts_count, num_posts_after)


class CommentsFormsTests(TestCase):

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='user', password='pass')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(author=self.user, text=TEXT_POST)
        self.add_comment = reverse('posts:add_comment', args=[self.post.id])
        self.comment_redirect = f'{LOGIN_URL}?next={self.add_comment}'
        self.comments_count = Comment.objects.count()
        self.form_data = {'text': 'тестовый коммент'}

    def test_unauthorized_client_cannot_create_comment(self):
        response = self.guest_client.post(
            self.add_comment, data=self.form_data, follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, self.comment_redirect)
        num_comments_after = Comment.objects.count()
        self.assertEqual(self.comments_count, num_comments_after)

    def test_authorized_client_can_create_comment(self):
        response = self.authorized_client.post(
            self.add_comment, data=self.form_data, follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        num_comments_after = Comment.objects.count()
        self.assertEqual(num_comments_after, self.comments_count + 1)
        test_comment = Comment.objects.latest('id')
        self.assertEqual(self.form_data['text'], test_comment.text)
