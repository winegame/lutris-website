"""Forms for the main app"""
# pylint: disable=missing-docstring,too-few-public-methods
import os
from datetime import date

import yaml

from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Submit, ButtonHolder, Fieldset, Field
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
from django_select2.forms import (
    ModelSelect2Widget,
    Select2MultipleWidget,
    Select2Widget, ModelSelect2MultipleWidget,
)
from bitfield.forms import BitFieldCheckboxSelectMultiple
from croppie.fields import CroppieField

from common.util import get_auto_increment_slug, slugify, load_yaml, dump_yaml
from games import models
from games.util.installer import validate_installer


class AutoSlugForm(forms.ModelForm):

    class Meta:
        # Override this in subclasses. Using a real model here not to confuse pylint
        model = models.Game
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(AutoSlugForm, self).__init__(*args, **kwargs)
        self.fields["slug"].required = False

    def get_slug(self, name, slug=None):
        return get_auto_increment_slug(self.Meta.model, self.instance, name, slug)

    def clean(self):
        self.cleaned_data["slug"] = self.get_slug(
            self.cleaned_data["name"], self.cleaned_data["slug"]
        )
        return self.cleaned_data


class BaseGameForm(AutoSlugForm):
    class Meta:
        model = models.Game
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(BaseGameForm, self).__init__(*args, **kwargs)
        self.fields["gogid"].required = False


class GameForm(forms.ModelForm):
    class Meta:
        model = models.Game
        fields = (
            "name",
            "year",
            "developer",
            "publisher",
            "website",
            "platforms",
            "genres",
            "description",
            "title_logo",
        )
        widgets = {
            "platforms": Select2MultipleWidget,
            "genres": Select2MultipleWidget,
            "developer": ModelSelect2Widget(
                model=models.Company, search_fields=["name__icontains"],
                attrs={'data-minimum-input-length': 0}
            ),
            "publisher": ModelSelect2Widget(
                model=models.Company, search_fields=["name__icontains"],
                attrs={'data-minimum-input-length': 0}
            ),
        }

    def __init__(self, *args, **kwargs):
        super(GameForm, self).__init__(*args, **kwargs)
        self.fields["name"].label = "游戏名称"
        self.fields["name"].help_text = (
            "如果游戏有英文名称，请添加“|”和英文名称，如“魔兽世界 | World of Warcraft”。"
        )
        self.fields["year"].label = "发行年份"
        self.fields["developer"].label = "开发商"
        self.fields["publisher"].label = "发行商"
        self.fields["website"].label = "官方网站"
        self.fields["website"].help_text = (
            "如果官网是游戏平台，请指向具体游戏页面。如果不存在，请留空。"
        )
        self.fields["platforms"].label = "平台"
        self.fields["genres"].label = "类型"
        self.fields["description"].label = "简介"
        self.fields["description"].help_text = (
            "如果可以找到，请复制游戏的官方描述，不要自己写。"
            "如果在官网找不到描述，或者描述不是中文，"
            "可以去<a href='https://baike.baidu.com/'>百度百科</a>或者"
            "<a href='https://www.3dmgame.com/'>3DM游戏网</a>找。"
        )

        self.fields["title_logo"] = CroppieField(
            options={
                "viewport": {"width": 875, "height": 345},
                "boundary": {"width": 875, "height": 345},
                "showZoomer": True,
            }
        )
        self.fields["title_logo"].label = "上传封面图像"
        self.fields["title_logo"].help_text = (
            "封面图像应该包含游戏名称。"
            "请确保图像不含透明部分，否则显示出来可能会很奇怪。"
            "如果图像是透明png，可以转存为jpg来消除透明部分。"
        )

        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            Fieldset(
                None,
                "name",
                "year",
                "developer",
                "publisher",
                "website",
                "platforms",
                "genres",
                "description",
                Field("title_logo", template="includes/upload_button.html"),
            ),
            ButtonHolder(Submit("submit", "提交")),
        )

    def rename_uploaded_file(self, file_field, cleaned_data, slug):
        if self.files.get(file_field):
            clean_field = cleaned_data.get(file_field)
            _, ext = os.path.splitext(clean_field.name)
            relpath = "games/banners/%s%s" % (slug, ext)
            clean_field.name = relpath
            current_abspath = os.path.join(settings.MEDIA_ROOT, relpath)
            if os.path.exists(current_abspath):
                os.remove(current_abspath)
            return clean_field
        return None

    def clean_name(self):
        name = self.cleaned_data["name"]
        slug = slugify(name)[:50]

        try:
            game = models.Game.objects.get(slug=slug)
        except models.Game.DoesNotExist:
            return name
        else:
            if game.is_public:
                msg = (
                    "该游戏已在我们的数据库中，<a href='/games/%s'>点击查看</a>。"
                ) % slug
            else:
                msg = (
                    "该游戏已在我们的数据库中但尚未发布（<a href='/games/%s'>点击查看</a>）。"
                    "欢迎与我们联系，以便我们尽快发布。"
                ) % slug
            raise forms.ValidationError(mark_safe(msg))


class GameEditForm(forms.ModelForm):
    """Form to suggest changes for games"""

    reason = forms.CharField(
        required=False,
        label="修改原因",
        help_text=(
            "请简要描述为什么要进行这些修改。"
            "如果可以，请添加信息来源（比如官网、百科、3DM链接等）。"
        ),
    )

    class Meta:
        """Form configuration"""

        model = models.Game
        fields = (
            "name",
            "year",
            "developer",
            "publisher",
            "website",
            "platforms",
            "genres",
            "description",
            "title_logo",
            "reason",
        )

        widgets = {
            "platforms": Select2MultipleWidget,
            "genres": Select2MultipleWidget,
            "developer": ModelSelect2Widget(
                model=models.Company, search_fields=["name__icontains"],
                attrs={'data-minimum-input-length': 0}
            ),
            "publisher": ModelSelect2Widget(
                model=models.Company, search_fields=["name__icontains"],
                attrs={'data-minimum-input-length': 0}
            ),
        }

    def __init__(self, payload, *args, **kwargs):
        super(GameEditForm, self).__init__(payload, *args, **kwargs)
        self.fields["name"].label = "游戏名称"
        self.fields["name"].help_text = (
            "如果游戏有英文名称，请添加“|”和英文名称，如“魔兽世界 | World of Warcraft”。"
        )
        self.fields["year"].label = "发行年份"
        self.fields["developer"].label = "开发商"
        self.fields["publisher"].label = "发行商"
        self.fields["website"].label = "官方网站"
        self.fields["website"].help_text = (
            "如果官网是游戏平台，请指向具体游戏页面。如果不存在，请留空。"
        )
        self.fields["platforms"].label = "平台"
        self.fields["genres"].label = "类型"
        self.fields["description"].label = "简介"
        self.fields["description"].help_text = (
            "如果可以找到，请复制游戏的官方描述，不要自己写。"
            "如果在官网找不到描述，或者描述不是中文，"
            "可以去<a href='https://baike.baidu.com/'>百度百科</a>或者"
            "<a href='https://www.3dmgame.com/'>3DM游戏网</a>找。"
        )

        self.fields["title_logo"] = CroppieField(
            options={
                "viewport": {"width": 875, "height": 345},
                "boundary": {"width": 875, "height": 345},
                "showZoomer": True,
                "url": payload["title_logo"].url if payload.get("title_logo") else "",
            }
        )
        self.fields["title_logo"].label = "上传封面图像"
        self.fields["title_logo"].help_text = (
            "封面图像应该包含游戏名称。"
            "请确保图像不含透明部分，否则显示出来可能会很奇怪。"
            "如果图像是透明png，可以转存为jpg来消除透明部分。"
        )
        self.fields["title_logo"].required = False

        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            Fieldset(
                None,
                "name",
                "year",
                "developer",
                "publisher",
                "website",
                "platforms",
                "genres",
                "description",
                Field("title_logo", template="includes/upload_button.html"),
                "reason",
            ),
            ButtonHolder(Submit("submit", "提交")),
        )

    def clean(self):
        """Overwrite clean to fail validation if unchanged form was submitted"""

        cleaned_data = super(GameEditForm, self).clean()

        # Raise error if nothing actually changed
        if not self.has_changed():
            raise forms.ValidationError("你没有进行任何修改")

        return cleaned_data


class ScreenshotForm(forms.ModelForm):
    class Meta:
        model = models.Screenshot
        fields = ("image", "description")

    def __init__(self, *args, **kwargs):
        self.game = models.Game.objects.get(pk=kwargs.pop("game_id"))
        super(ScreenshotForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "提交"))

    def save(self, commit=True):
        self.instance.game = self.game
        return super().save(commit=commit)


class InstallerForm(forms.ModelForm):
    """Form to create and modify installers"""

    class Meta:
        """Form configuration"""

        model = models.Installer
        fields = ("runner", "version", "description", "notes", "content", "draft")
        widgets = {
            "runner": Select2Widget,
            "description": forms.Textarea(attrs={"class": "installer-textarea"}),
            "notes": forms.Textarea(attrs={"class": "installer-textarea"}),
            "content": forms.Textarea(
                attrs={"class": "code-editor", "spellcheck": "false"}
            ),
            "draft": forms.HiddenInput,
        }
        help_texts = {
            "version": (
                "简短版本名称，描述安装程序针对的游戏版本。可以是发行名称（例如“GOTY”、“Gold”），格式（例如“CD”），运行平台（例如“x86”、“x64”、“arm64”），也可以是发行平台（例如“Steam”、“UPlay”）或游戏的实际版本号。"
            ),
            "description": (
                "安装脚本的简单介绍。"
                "注意：不要添加游戏简介，只介绍你的安装脚本就好。"
            ),
            "notes": (
                "描述安装游戏时需要手动进行的操作，或运行游戏时的任何已知问题。"
            ),
        }

    def __init__(self, *args, **kwargs):
        super(InstallerForm, self).__init__(*args, **kwargs)
        self.fields["runner"].label = "运行环境"
        self.fields["version"].label = "版本"
        self.fields["description"].label = "安装脚本简介"
        self.fields["notes"].label = "技术性说明"

    def clean_content(self):
        """Verify that the content field is valid yaml"""
        yaml_data = self.cleaned_data["content"]
        try:
            yaml_data = load_yaml(yaml_data)
        except yaml.error.MarkedYAMLError as ex:
            raise forms.ValidationError(
                "YAML错误，位置: 第 %s 行，错误: %s"
                % (ex.problem_mark.line, ex.problem)
            )
        return dump_yaml(yaml_data)

    def clean_version(self):
        version = self.cleaned_data["version"]
        if not version:
            raise forms.ValidationError("此字段是必填字段")
        if version.lower() == "change me" or version.lower() == "请修改该字段":
            raise forms.ValidationError('请修改该字段')
        #if version.lower().endswith("version") or \
        #   version.lower().endswith("版本") or \
        #   version.lower().endswith("版"):
        #    raise forms.ValidationError(
        #        "不要把“version”、“版本”或“版”字放在版本字段的末尾"
        #    )
        version_exists = (
            models.Installer.objects.filter(game=self.instance.game, version=version)
            .exclude(id=self.instance.id)
            .count()
        )
        if version_exists:
            raise forms.ValidationError(
                "相同版本的安装脚本已存在，如需继续提交，请修改版本字段"
            )
        return version

    def clean(self):
        dummy_installer = models.Installer(game=self.instance.game, **self.cleaned_data)
        is_valid, errors = validate_installer(dummy_installer)
        if not is_valid:
            if "content" not in self.errors:
                self.errors["content"] = []
            for error in errors:
                self.errors["content"].append(error)
            raise forms.ValidationError("安装脚本错误")
        # Draft status depends on the submit button clicked
        self.cleaned_data["draft"] = "save" in self.data
        return self.cleaned_data


class InstallerEditForm(InstallerForm):
    """Form to edit an installer"""

    class Meta(InstallerForm.Meta):
        """Form configuration"""

        fields = [
            "runner",
            "version",
            "description",
            "notes",
            "reason",
            "content",
            "draft",
        ]

    reason = forms.CharField(
        widget=forms.Textarea(attrs={"class": "installer-textarea"}),
        required=False,
        label="修改原因",
        help_text="请简要描述为什么要进行这些修改，"
        "这有助于加快我们审核。",
    )


class ForkInstallerForm(forms.ModelForm):
    class Meta:
        model = models.Installer
        fields = ("game",)
        widgets = {
            "game": ModelSelect2Widget(
                model=models.Game, search_fields=["name__icontains"]
            )
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["game"].label = "游戏"


class LibraryFilterForm(forms.Form):
    q = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"style": "width: 100%;",
                                      "class": "select2-lookalike"}),
        required=False,
        label="游戏名称"
    )
    platforms = forms.MultipleChoiceField(
        widget=Select2MultipleWidget(
            attrs={'data-width': '100%',
                   'data-close-on-select': 'false',
                   'data-placeholder': '',
                   'data-minimum-input-length': 0}
        ),
        required=False,
        label="平台"
    )
    genres = forms.ModelMultipleChoiceField(
        queryset=models.Genre.objects.all(),
        widget=ModelSelect2MultipleWidget(
            model=models.Genre,
            search_fields=['name__icontains'],
            attrs={'data-width': '100%',
                   'data-close-on-select': 'false',
                   'data-placeholder': '',
                   'data-minimum-input-length': 0}
        ),
        required=False,
        label="类型"
    )
    companies = forms.ModelMultipleChoiceField(
        queryset=models.Company.objects.all(),
        widget=ModelSelect2MultipleWidget(
            model=models.Company,
            search_fields=['name__icontains'],
            attrs={'data-width': '100%',
                   'data-close-on-select': 'false',
                   'data-placeholder': '',
                   'data-minimum-input-length': 0}
        ),
        required=False,
        label="开发商"
    )
    years = forms.MultipleChoiceField(
        choices=[(i, i) for i in range(date.today().year, 1970, -1)],
        widget=Select2MultipleWidget(attrs={'data-width': '100%',
                                            'data-close-on-select': 'false',
                                            'data-placeholder': ''}),
        required=False,
        label="发行年份"
    )
    flags = forms.MultipleChoiceField(
        choices=models.Game.GAME_FLAGS,
        widget=BitFieldCheckboxSelectMultiple,
        required=False,
        label="其他选项"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['platforms'].choices = (models.Platform.objects.values_list('pk', 'name'))
