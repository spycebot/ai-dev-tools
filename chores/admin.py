from django.contrib import admin
from .models import Chore


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ('description', 'priority', 'status', 'created_at', 'completed_by')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('description', 'completed_by')
    readonly_fields = ('created_at', 'completed_at')
    
    fieldsets = (
        ('Chore Details', {
            'fields': ('description', 'priority', 'status')
        }),
        ('Completion Info', {
            'fields': ('completed_by', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
