/****************************************************************************
** ui.h extension file, included from the uic-generated form implementation.
**
** If you wish to add, delete or rename slots use Qt Designer which will
** update this file, preserving your code. Create an init() slot in place of
** a constructor, and a destroy() slot in place of a destructor.
*****************************************************************************/

void SourceOptionsDialog::init()
{
print "Disabling sorting for RuleList"
self.RuleList.setSorting(-1)
}

void SourceOptionsDialog::OkButton_clicked()
{
self.accept()
}


void SourceOptionsDialog::CancelButton_clicked()
{
self.reject()
}

