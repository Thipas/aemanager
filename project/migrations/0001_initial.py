# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    depends_on = (
        ("contact", "0001_initial"),
    )

    def forwards(self, orm):

        # Adding model 'Contract'
        db.create_table('project_contract', (
            ('ownedobject_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.OwnedObject'], unique=True, primary_key=True)),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contracts', to=orm['contact.Contact'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('update_date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('project', ['Contract'])

        # Adding model 'Project'
        db.create_table('project_project', (
            ('ownedobject_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.OwnedObject'], unique=True, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contact.Contact'], null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=1)),
        ))
        db.send_create_signal('project', ['Project'])

        # Adding model 'Proposal'
        db.create_table('project_proposal', (
            ('ownedobject_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.OwnedObject'], unique=True, primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['project.Project'])),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=12, decimal_places=2, blank=True)),
            ('begin_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('contract_content', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('update_date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('project', ['Proposal'])

        # Adding model 'Invoice'
        db.create_table('project_invoice', (
            ('ownedobject_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.OwnedObject'], unique=True, primary_key=True)),
            ('proposal', self.gf('django.db.models.fields.related.ForeignKey')(related_name='invoices', to=orm['project.Proposal'])),
            ('invoice_id', self.gf('django.db.models.fields.IntegerField')()),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=12, decimal_places=2, blank=True)),
            ('edition_date', self.gf('django.db.models.fields.DateField')()),
            ('payment_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('paid_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('execution_begin_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('execution_end_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('penalty_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('penalty_rate', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=4, decimal_places=2, blank=True)),
            ('discount_conditions', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('balance_payments', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('project', ['Invoice'])

        # Adding model 'ProposalRow'
        db.create_table('project_proposalrow', (
            ('ownedobject_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.OwnedObject'], unique=True, primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('category', self.gf('django.db.models.fields.IntegerField')()),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=1)),
            ('unit_price', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
            ('proposal', self.gf('django.db.models.fields.related.ForeignKey')(related_name='proposal_rows', to=orm['project.Proposal'])),
        ))
        db.send_create_signal('project', ['ProposalRow'])

        # Adding model 'InvoiceRow'
        db.create_table('project_invoicerow', (
            ('ownedobject_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.OwnedObject'], unique=True, primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('category', self.gf('django.db.models.fields.IntegerField')()),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=1)),
            ('unit_price', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
            ('invoice', self.gf('django.db.models.fields.related.ForeignKey')(related_name='invoice_rows', to=orm['project.Invoice'])),
        ))
        db.send_create_signal('project', ['InvoiceRow'])


    def backwards(self, orm):

        # Deleting model 'Contract'
        db.delete_table('project_contract')

        # Deleting model 'Project'
        db.delete_table('project_project')

        # Deleting model 'Proposal'
        db.delete_table('project_proposal')

        # Deleting model 'Invoice'
        db.delete_table('project_invoice')

        # Deleting model 'ProposalRow'
        db.delete_table('project_proposalrow')

        # Deleting model 'InvoiceRow'
        db.delete_table('project_invoicerow')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contact.address': {
            'Meta': {'object_name': 'Address', '_ormbases': ['core.OwnedObject']},
            'city': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contact.Country']", 'null': 'True', 'blank': 'True'}),
            'ownedobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.OwnedObject']", 'unique': 'True', 'primary_key': 'True'}),
            'street': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'zipcode': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'})
        },
        'contact.contact': {
            'Meta': {'object_name': 'Contact', '_ormbases': ['core.OwnedObject']},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contact.Address']"}),
            'company_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'blank': 'True'}),
            'contact_type': ('django.db.models.fields.IntegerField', [], {}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['contact.Contact']", 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'default': "''", 'max_length': '75', 'blank': 'True'}),
            'firstname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'function': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'legal_form': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ownedobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.OwnedObject']", 'unique': 'True', 'primary_key': 'True'}),
            'representative': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'representative_function': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'})
        },
        'contact.country': {
            'Meta': {'ordering': "['country_name']", 'object_name': 'Country'},
            'country_code2': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'country_code3': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'country_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'core.ownedobject': {
            'Meta': {'object_name': 'OwnedObject'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'project.contract': {
            'Meta': {'object_name': 'Contract', '_ormbases': ['core.OwnedObject']},
            'content': ('django.db.models.fields.TextField', [], {}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contracts'", 'to': "orm['contact.Contact']"}),
            'ownedobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.OwnedObject']", 'unique': 'True', 'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'update_date': ('django.db.models.fields.DateField', [], {})
        },
        'project.invoice': {
            'Meta': {'object_name': 'Invoice', '_ormbases': ['core.OwnedObject']},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '12', 'decimal_places': '2', 'blank': 'True'}),
            'balance_payments': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'discount_conditions': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'edition_date': ('django.db.models.fields.DateField', [], {}),
            'execution_begin_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'execution_end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'invoice_id': ('django.db.models.fields.IntegerField', [], {}),
            'ownedobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.OwnedObject']", 'unique': 'True', 'primary_key': 'True'}),
            'paid_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'payment_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'penalty_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'penalty_rate': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '4', 'decimal_places': '2', 'blank': 'True'}),
            'proposal': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'invoices'", 'to': "orm['project.Proposal']"}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'project.invoicerow': {
            'Meta': {'object_name': 'InvoiceRow'},
            'category': ('django.db.models.fields.IntegerField', [], {}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'invoice_rows'", 'to': "orm['project.Invoice']"}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ownedobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.OwnedObject']", 'unique': 'True', 'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '1'}),
            'unit_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'})
        },
        'project.project': {
            'Meta': {'object_name': 'Project', '_ormbases': ['core.OwnedObject']},
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contact.Contact']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ownedobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.OwnedObject']", 'unique': 'True', 'primary_key': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'project.proposal': {
            'Meta': {'object_name': 'Proposal', '_ormbases': ['core.OwnedObject']},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '12', 'decimal_places': '2', 'blank': 'True'}),
            'begin_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'contract_content': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'ownedobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.OwnedObject']", 'unique': 'True', 'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['project.Project']"}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'update_date': ('django.db.models.fields.DateField', [], {})
        },
        'project.proposalrow': {
            'Meta': {'object_name': 'ProposalRow'},
            'category': ('django.db.models.fields.IntegerField', [], {}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ownedobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.OwnedObject']", 'unique': 'True', 'primary_key': 'True'}),
            'proposal': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'proposal_rows'", 'to': "orm['project.Proposal']"}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '1'}),
            'unit_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'})
        }
    }

    complete_apps = ['project']
