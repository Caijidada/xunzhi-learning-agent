"""Reversible course routing. Original units and source references stay intact."""
import re


def default_route(title):
    title = re.sub(r'^[\d\s.、一二三四五六七八九十]+', '', title).strip().lower()
    if title in {'致谢', '鸣谢', '版权', '版权声明', '出版信息', 'acknowledgments', 'acknowledgements', 'copyright'}:
        return {'category': 'skip', 'reason': '出版附属内容，默认不纳入学习路径；仍可展开查看。'}
    if title in {'引言', '前言', '序言', '全书结构', '如何阅读本书', '如何使用本书', '前置知识', 'preface', 'introduction'}:
        return {'category': 'guide', 'reason': '作为可选导读保留，可直接进入正文；可让模型结合原文重新判断。'}
    return {'category': 'learn', 'reason': ''}


def route_units(course, units):
    choices = course.get('curriculum', {})
    return [{**u, **choices.get(u['id'], default_route(u['title']))} for u in units]
