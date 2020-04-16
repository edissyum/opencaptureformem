<?php

/**
* Copyright Maarch since 2008 under licence GPLv3.
* See LICENCE.txt file at the root folder for more details.
* This file is part of Maarch software.
*
*/

/**
* @brief Rest Routes File
* @author dev@maarch.org
*/

require '../vendor/autoload.php';

//Root application position
chdir('..');
date_default_timezone_set(\SrcCore\models\CoreConfigModel::getTimezone());

$customId = \SrcCore\models\CoreConfigModel::getCustomId();
$language = \SrcCore\models\CoreConfigModel::getLanguage();
if (file_exists("custom/{$customId}/src/core/lang/lang-{$language}.php")) {
    require_once("custom/{$customId}/src/core/lang/lang-{$language}.php");
}
require_once("src/core/lang/lang-{$language}.php");

$app = new \Slim\App(['settings' => ['displayErrorDetails' => true, 'determineRouteBeforeAppMiddleware' => true, 'addContentLengthHeader' => true ]]);

//Authentication
$app->add(function (\Slim\Http\Request $request, \Slim\Http\Response $response, callable $next) {
    $routesWithoutAuthentication = ['GET/jnlp/{jnlpUniqueId}', 'POST/password', 'PUT/password', 'GET/passwordRules', 'GET/onlyOffice/mergedFile', 'POST/onlyOfficeCallback'];
    $route = $request->getAttribute('route');
    $currentMethod = empty($route) ? '' : $route->getMethods()[0];
    $currentRoute = empty($route) ? '' : $route->getPattern();
    if (!in_array($currentMethod.$currentRoute, $routesWithoutAuthentication)) {
        $login = \SrcCore\controllers\AuthenticationController::authentication();
        if (!empty($login)) {
            \SrcCore\controllers\CoreController::setGlobals(['login' => $login]);
            if (!empty($currentRoute)) {
                $r = \SrcCore\controllers\AuthenticationController::isRouteAvailable(['login' => $login, 'currentRoute' => $currentRoute]);
                if (!$r['isRouteAvailable']) {
                    return $response->withStatus(405)->withJson(['errors' => $r['errors']]);
                }
            }
        } elseif ($currentMethod.$currentRoute != 'GET/initialize') {
            return $response->withStatus(401)->withJson(['errors' => 'Authentication Failed']);
        }
    }
    $response = $next($request, $response);
    return $response;
});

//Initialize
$app->get('/initialize', \SrcCore\controllers\CoreController::class . ':initialize');

//Acknowledgement Receipt
$app->post('/acknowledgementReceipts', \AcknowledgementReceipt\controllers\AcknowledgementReceiptController::class . ':createPaperAcknowledgement');
$app->get('/acknowledgementReceipts/{id}', \AcknowledgementReceipt\controllers\AcknowledgementReceiptController::class . ':getById');
$app->get('/acknowledgementReceipts/{id}/content', \AcknowledgementReceipt\controllers\AcknowledgementReceiptController::class . ':getAcknowledgementReceipt');

//Actions
$app->get('/actions', \Action\controllers\ActionController::class . ':get');
$app->get('/initAction', \Action\controllers\ActionController::class . ':initAction');
$app->get('/actions/{id}', \Action\controllers\ActionController::class . ':getById');
$app->post('/actions', \Action\controllers\ActionController::class . ':create');
$app->put('/actions/{id}', \Action\controllers\ActionController::class . ':update');
$app->delete('/actions/{id}', \Action\controllers\ActionController::class . ':delete');

//Administration
$app->get('/administration/details', \Administration\controllers\AdministrationController::class . ':getDetails');

//Attachments
$app->post('/attachments', \Attachment\controllers\AttachmentController::class . ':create');
$app->get('/attachments/{id}', \Attachment\controllers\AttachmentController::class . ':getById');
$app->put('/attachments/{id}', \Attachment\controllers\AttachmentController::class . ':update');
$app->delete('/attachments/{id}', \Attachment\controllers\AttachmentController::class . ':delete');
$app->get('/attachments/{id}/content', \Attachment\controllers\AttachmentController::class . ':getFileContent');
$app->get('/attachments/{id}/originalContent', \Attachment\controllers\AttachmentController::class . ':getOriginalFileContent');
$app->get('/attachments/{id}/thumbnail', \Attachment\controllers\AttachmentController::class . ':getThumbnailContent');
$app->put('/attachments/{id}/inSendAttachment', \Attachment\controllers\AttachmentController::class . ':setInSendAttachment');
$app->put('/attachments/{id}/inSignatureBook', \Attachment\controllers\AttachmentController::class . ':setInSignatureBook');
$app->put('/attachments/{id}/sign', \SignatureBook\controllers\SignatureBookController::class . ':signAttachment');
$app->put('/attachments/{id}/unsign', \SignatureBook\controllers\SignatureBookController::class . ':unsignAttachment');
$app->post('/attachments/{id}/mailing', \Attachment\controllers\AttachmentController::class . ':getMailingById');
$app->get('/attachmentsInformations', \Attachment\controllers\AttachmentController::class . ':getByChrono');
$app->get('/attachmentsTypes', \Attachment\controllers\AttachmentController::class . ':getAttachmentsTypes');

//AutoComplete
$app->get('/autocomplete/users', \SrcCore\controllers\AutoCompleteController::class . ':getUsers');
$app->get('/autocomplete/maarchParapheurUsers', \SrcCore\controllers\AutoCompleteController::class . ':getMaarchParapheurUsers');
$app->get('/autocomplete/correspondents', \SrcCore\controllers\AutoCompleteController::class . ':getCorrespondents');
$app->get('/autocomplete/contacts', \SrcCore\controllers\AutoCompleteController::class . ':getContacts');
$app->get('/autocomplete/contacts/company', \SrcCore\controllers\AutoCompleteController::class . ':getContactsCompany');
$app->get('/autocomplete/users/administration', \SrcCore\controllers\AutoCompleteController::class . ':getUsersForAdministration');
$app->get('/autocomplete/users/circuit', \SrcCore\controllers\AutoCompleteController::class . ':getUsersForCircuit');
$app->get('/autocomplete/entities', \SrcCore\controllers\AutoCompleteController::class . ':getEntities');
$app->get('/autocomplete/statuses', \SrcCore\controllers\AutoCompleteController::class . ':getStatuses');
$app->get('/autocomplete/banAddresses', \SrcCore\controllers\AutoCompleteController::class . ':getBanAddresses');
$app->get('/autocomplete/folders', \SrcCore\controllers\AutoCompleteController::class . ':getFolders');
$app->get('/autocomplete/tags', \SrcCore\controllers\AutoCompleteController::class . ':getTags');
$app->get('/autocomplete/ouM2MAnnuary', \SrcCore\controllers\AutoCompleteController::class . ':getOuM2MAnnuary');
$app->get('/autocomplete/businessIdM2MAnnuary', \SrcCore\controllers\AutoCompleteController::class . ':getBusinessIdM2MAnnuary');
$app->get('/autocomplete/contacts/m2m', \SrcCore\controllers\AutoCompleteController::class . ':getAvailableContactsForM2M');

//Baskets
$app->get('/baskets', \Basket\controllers\BasketController::class . ':get');
$app->post('/baskets', \Basket\controllers\BasketController::class . ':create');
$app->get('/baskets/{id}', \Basket\controllers\BasketController::class . ':getById');
$app->put('/baskets/{id}', \Basket\controllers\BasketController::class . ':update');
$app->delete('/baskets/{id}', \Basket\controllers\BasketController::class . ':delete');
$app->get('/baskets/{id}/groups', \Basket\controllers\BasketController::class . ':getGroups');
$app->post('/baskets/{id}/groups', \Basket\controllers\BasketController::class . ':createGroup');
$app->put('/baskets/{id}/groups/{groupId}', \Basket\controllers\BasketController::class . ':updateGroup');
$app->put('/baskets/{id}/groups/{groupId}/actions', \Basket\controllers\BasketController::class . ':updateGroupActions');
$app->delete('/baskets/{id}/groups/{groupId}', \Basket\controllers\BasketController::class . ':deleteGroup');
$app->get('/sortedBaskets', \Basket\controllers\BasketController::class . ':getSorted');
$app->put('/sortedBaskets/{id}', \Basket\controllers\BasketController::class . ':updateSort');

//Configurations
$app->get('/configurations/{service}', \Configuration\controllers\ConfigurationController::class . ':getByService');
$app->put('/configurations/{service}', \Configuration\controllers\ConfigurationController::class . ':update');

//Contacts
$app->get('/contacts', \Contact\controllers\ContactController::class . ':get');
$app->post('/contacts', \Contact\controllers\ContactController::class . ':create');
$app->get('/contacts/{id}', \Contact\controllers\ContactController::class . ':getById');
$app->put('/contacts/{id}', \Contact\controllers\ContactController::class . ':update');
$app->delete('/contacts/{id}', \Contact\controllers\ContactController::class . ':delete');
$app->put('/contacts/{id}/activation', \Contact\controllers\ContactController::class . ':updateActivation');
$app->get('/formattedContacts/{id}/types/{type}', \Contact\controllers\ContactController::class . ':getLightFormattedContact');
$app->get('/ban/availableDepartments', \Contact\controllers\ContactController::class . ':getAvailableDepartments');
$app->post('/contacts/formatV1', \Contact\controllers\ContactController::class . ':getFormattedContactsForSearchV1');

//ContactsCustomFields
$app->get('/contactsCustomFields', \Contact\controllers\ContactCustomFieldController::class . ':get');
$app->post('/contactsCustomFields', \Contact\controllers\ContactCustomFieldController::class . ':create');
$app->put('/contactsCustomFields/{id}', \Contact\controllers\ContactCustomFieldController::class . ':update');
$app->delete('/contactsCustomFields/{id}', \Contact\controllers\ContactCustomFieldController::class . ':delete');

//ContactsGroups
$app->get('/contactsGroups', \Contact\controllers\ContactGroupController::class . ':get');
$app->post('/contactsGroups', \Contact\controllers\ContactGroupController::class . ':create');
$app->get('/contactsGroups/{id}', \Contact\controllers\ContactGroupController::class . ':getById');
$app->put('/contactsGroups/{id}', \Contact\controllers\ContactGroupController::class . ':update');
$app->delete('/contactsGroups/{id}', \Contact\controllers\ContactGroupController::class . ':delete');
$app->post('/contactsGroups/{id}/contacts', \Contact\controllers\ContactGroupController::class . ':addContacts');
$app->delete('/contactsGroups/{id}/contacts/{contactId}', \Contact\controllers\ContactGroupController::class . ':deleteContact');
$app->get('/contactsParameters', \Contact\controllers\ContactController::class . ':getContactsParameters');
$app->put('/contactsParameters', \Contact\controllers\ContactController::class . ':updateContactsParameters');
$app->get('/civilities', \Contact\controllers\ContactController::class . ':getCivilities');

//Convert
$app->post('/convertedFile', \Convert\controllers\ConvertPdfController::class . ':convertedFile');
$app->get('/convertedFile/{filename}', \Convert\controllers\ConvertPdfController::class . ':getConvertedFileByFilename');
$app->post('/convertedFile/encodedFile', \Convert\controllers\ConvertPdfController::class . ':getConvertedFileFromEncodedFile');

//ContentManagement
$app->post('/jnlp', \ContentManagement\controllers\JnlpController::class . ':generateJnlp');
$app->get('/jnlp/{jnlpUniqueId}', \ContentManagement\controllers\JnlpController::class . ':renderJnlp');
$app->post('/jnlp/{jnlpUniqueId}', \ContentManagement\controllers\JnlpController::class . ':processJnlp');
$app->get('/jnlp/lock/{jnlpUniqueId}', \ContentManagement\controllers\JnlpController::class . ':isLockFileExisting');
$app->get('/documentEditors', \ContentManagement\controllers\DocumentEditorController::class . ':get');
$app->get('/onlyOffice/configuration', \ContentManagement\controllers\OnlyOfficeController::class . ':getConfiguration');
$app->post('/onlyOffice/mergedFile', \ContentManagement\controllers\OnlyOfficeController::class . ':saveMergedFile');
$app->get('/onlyOffice/mergedFile', \ContentManagement\controllers\OnlyOfficeController::class . ':getMergedFile');
$app->get('/onlyOffice/encodedFile', \ContentManagement\controllers\OnlyOfficeController::class . ':getEncodedFileFromUrl');
$app->get('/onlyOffice/available', \ContentManagement\controllers\OnlyOfficeController::class . ':isAvailable');
$app->post('/onlyOfficeCallback', function (\Slim\Http\Request $request, \Slim\Http\Response $response) {
    return $response->withJson(['error' => 0]);
});

//CustomFields
$app->get('/customFields', \CustomField\controllers\CustomFieldController::class . ':get');
$app->post('/customFields', \CustomField\controllers\CustomFieldController::class . ':create');
$app->put('/customFields/{id}', \CustomField\controllers\CustomFieldController::class . ':update');
$app->delete('/customFields/{id}', \CustomField\controllers\CustomFieldController::class . ':delete');

//Docservers
$app->get('/docservers', \Docserver\controllers\DocserverController::class . ':get');
$app->post('/docservers', \Docserver\controllers\DocserverController::class . ':create');
$app->get('/docservers/{id}', \Docserver\controllers\DocserverController::class . ':getById');
$app->put('/docservers/{id}', \Docserver\controllers\DocserverController::class . ':update');
$app->delete('/docservers/{id}', \Docserver\controllers\DocserverController::class . ':delete');

//DocserverTypes
$app->get('/docserverTypes', \Docserver\controllers\DocserverTypeController::class . ':get');
$app->get('/docserverTypes/{id}', \Docserver\controllers\DocserverTypeController::class . ':getById');

//doctypes
$app->get('/doctypes', \Doctype\controllers\FirstLevelController::class . ':getTree');
$app->post('/doctypes/firstLevel', \Doctype\controllers\FirstLevelController::class . ':create');
$app->get('/doctypes/firstLevel/{id}', \Doctype\controllers\FirstLevelController::class . ':getById');
$app->put('/doctypes/firstLevel/{id}', \Doctype\controllers\FirstLevelController::class . ':update');
$app->delete('/doctypes/firstLevel/{id}', \Doctype\controllers\FirstLevelController::class . ':delete');
$app->post('/doctypes/secondLevel', \Doctype\controllers\SecondLevelController::class . ':create');
$app->get('/doctypes/secondLevel/{id}', \Doctype\controllers\SecondLevelController::class . ':getById');
$app->put('/doctypes/secondLevel/{id}', \Doctype\controllers\SecondLevelController::class . ':update');
$app->delete('/doctypes/secondLevel/{id}', \Doctype\controllers\SecondLevelController::class . ':delete');
$app->get('/doctypes/types', \Doctype\controllers\DoctypeController::class . ':get');
$app->post('/doctypes/types', \Doctype\controllers\DoctypeController::class . ':create');
$app->get('/doctypes/types/{id}', \Doctype\controllers\DoctypeController::class . ':getById');
$app->put('/doctypes/types/{id}', \Doctype\controllers\DoctypeController::class . ':update');
$app->delete('/doctypes/types/{id}', \Doctype\controllers\DoctypeController::class . ':delete');
$app->put('/doctypes/types/{id}/redirect', \Doctype\controllers\DoctypeController::class . ':deleteRedirect');
$app->get('/administration/doctypes/new', \Doctype\controllers\FirstLevelController::class . ':initDoctypes');

//Emails
$app->post('/emails', \Email\controllers\EmailController::class . ':send');
$app->get('/emails/{id}', \Email\controllers\EmailController::class . ':getById');
$app->put('/emails/{id}', \Email\controllers\EmailController::class . ':update');
$app->delete('/emails/{id}', \Email\controllers\EmailController::class . ':delete');

//Entities
$app->get('/entities', \Entity\controllers\EntityController::class . ':get');
$app->post('/entities', \Entity\controllers\EntityController::class . ':create');
$app->get('/entities/{id}', \Entity\controllers\EntityController::class . ':getById');
$app->put('/entities/{id}', \Entity\controllers\EntityController::class . ':update');
$app->delete('/entities/{id}', \Entity\controllers\EntityController::class . ':delete');
$app->get('/entities/{id}/details', \Entity\controllers\EntityController::class . ':getDetailledById');
$app->get('/entities/{id}/users', \Entity\controllers\EntityController::class . ':getUsersById');
$app->put('/entities/{id}/reassign/{newEntityId}', \Entity\controllers\EntityController::class . ':reassignEntity');
$app->put('/entities/{id}/status', \Entity\controllers\EntityController::class . ':updateStatus');
$app->put('/entities/{id}/annuaries', \MessageExchange\controllers\AnnuaryController::class . ':updateEntityToOrganization');
$app->get('/entityTypes', \Entity\controllers\EntityController::class . ':getTypes');
$app->post('/entitySeparators', \Entity\controllers\EntitySeparatorController::class . ':create');

//ExternalSignatoryBook
$app->get('/xParaphWorkflow', \ExternalSignatoryBook\controllers\XParaphController::class . ':getWorkflow');
$app->post('/xParaphAccount', \ExternalSignatoryBook\controllers\XParaphController::class . ':createXparaphAccount');
$app->delete('/xParaphAccount', \ExternalSignatoryBook\controllers\XParaphController::class . ':deleteXparaphAccount');

//Folders
$app->get('/folders', \Folder\controllers\FolderController::class . ':get');
$app->post('/folders', \Folder\controllers\FolderController::class . ':create');
$app->get('/folders/{id}', \Folder\controllers\FolderController::class . ':getById');
$app->put('/folders/{id}', \Folder\controllers\FolderController::class . ':update');
$app->delete('/folders/{id}', \Folder\controllers\FolderController::class . ':delete');
$app->get('/folders/{id}/resources', \Folder\controllers\FolderController::class . ':getResourcesById');
$app->post('/folders/{id}/resources', \Folder\controllers\FolderController::class . ':addResourcesById');
$app->delete('/folders/{id}/resources', \Folder\controllers\FolderController::class . ':removeResourcesById');
$app->get('/folders/{id}/resources/{resId}/baskets', \Folder\controllers\FolderController::class . ':getBasketsFromFolder');
$app->get('/folders/{id}/filters', \Folder\controllers\FolderController::class . ':getFilters');
$app->put('/folders/{id}/sharing', \Folder\controllers\FolderController::class . ':sharing');
$app->get('/pinnedFolders', \Folder\controllers\FolderController::class . ':getPinnedFolders');
$app->post('/folders/{id}/pin', \Folder\controllers\FolderController::class . ':pinFolder');
$app->delete('/folders/{id}/unpin', \Folder\controllers\FolderController::class . ':unpinFolder');

//Groups
$app->get('/groups', \Group\controllers\GroupController::class . ':get');
$app->post('/groups', \Group\controllers\GroupController::class . ':create');
$app->get('/groups/{id}', \Group\controllers\GroupController::class . ':getById');
$app->put('/groups/{id}', \Group\controllers\GroupController::class . ':update');
$app->delete('/groups/{id}', \Group\controllers\GroupController::class . ':delete');
$app->get('/groups/{id}/details', \Group\controllers\GroupController::class . ':getDetailledById');
$app->get('/groups/{id}/indexing', \Group\controllers\GroupController::class . ':getIndexingInformationsById');
$app->put('/groups/{id}/indexing', \Group\controllers\GroupController::class . ':updateIndexingInformations');
$app->put('/groups/{id}/reassign/{newGroupId}', \Group\controllers\GroupController::class . ':reassignUsers');
$app->post('/groups/{id}/privileges/{privilegeId}', \Group\controllers\PrivilegeController::class . ':addPrivilege');
$app->delete('/groups/{id}/privileges/{privilegeId}', \Group\controllers\PrivilegeController::class . ':removePrivilege');
$app->put('/groups/{id}/privileges/{privilegeId}/parameters', \Group\controllers\PrivilegeController::class . ':updateParameters');
$app->get('/groups/{id}/privileges/{privilegeId}/parameters', \Group\controllers\PrivilegeController::class . ':getParameters');

//History
$app->get('/history', \History\controllers\HistoryController::class . ':get');
$app->get('/history/availableFilters', \History\controllers\HistoryController::class . ':getAvailableFilters');
$app->get('/history/users/{userSerialId}', \History\controllers\HistoryController::class . ':getByUserId');

//BatchHistory
$app->get('/batchHistory', \History\controllers\BatchHistoryController::class . ':get');
$app->get('/batchHistory/availableFilters', \History\controllers\BatchHistoryController::class . ':getAvailableFilters');

//Header
$app->get('/header', \SrcCore\controllers\CoreController::class . ':getHeader');

//Home
$app->get('/home', \Home\controllers\HomeController::class . ':get');
$app->get('/home/lastRessources', \Home\controllers\HomeController::class . ':getLastRessources');
$app->get('/home/maarchParapheurDocuments', \Home\controllers\HomeController::class . ':getMaarchParapheurDocuments');

//Indexing
$app->get('/indexing/groups/{groupId}/actions', \Resource\controllers\IndexingController::class . ':getIndexingActions');
$app->get('/indexing/groups/{groupId}/entities', \Resource\controllers\IndexingController::class . ':getIndexingEntities');
$app->get('/indexing/processLimitDate', \Resource\controllers\IndexingController::class . ':getProcessLimitDate');
$app->get('/indexing/fileInformations', \Resource\controllers\IndexingController::class . ':getFileInformations');
$app->get('/indexing/priority', \Resource\controllers\IndexingController::class . ':getPriorityWithProcessLimitDate');
$app->put('/indexing/groups/{groupId}/actions/{actionId}', \Resource\controllers\IndexingController::class . ':setAction');

//IndexingModels
$app->get('/indexingModels', \IndexingModel\controllers\IndexingModelController::class . ':get');
$app->get('/indexingModels/entities', \IndexingModel\controllers\IndexingModelController::class . ':getEntities');
$app->get('/indexingModels/{id}', \IndexingModel\controllers\IndexingModelController::class . ':getById');
$app->post('/indexingModels', \IndexingModel\controllers\IndexingModelController::class . ':create');
$app->put('/indexingModels/{id}', \IndexingModel\controllers\IndexingModelController::class . ':update');
$app->put('/indexingModels/{id}/disable', \IndexingModel\controllers\IndexingModelController::class . ':disable');
$app->put('/indexingModels/{id}/enable', \IndexingModel\controllers\IndexingModelController::class . ':enable');
$app->delete('/indexingModels/{id}', \IndexingModel\controllers\IndexingModelController::class . ':delete');

//ListInstances
$app->get('/listinstance/{id}', \Entity\controllers\ListInstanceController::class . ':getById');
$app->put('/listinstances', \Entity\controllers\ListInstanceController::class . ':update');

//ListTemplates
$app->get('/listTemplates', \Entity\controllers\ListTemplateController::class . ':get');
$app->post('/listTemplates', \Entity\controllers\ListTemplateController::class . ':create');
$app->get('/listTemplates/{id}', \Entity\controllers\ListTemplateController::class . ':getById');
$app->put('/listTemplates/{id}', \Entity\controllers\ListTemplateController::class . ':update');
$app->delete('/listTemplates/{id}', \Entity\controllers\ListTemplateController::class . ':delete');
$app->get('/listTemplates/entities/{entityId}', \Entity\controllers\ListTemplateController::class . ':getByEntityId');
$app->put('/listTemplates/entityDest/itemId/{itemId}', \Entity\controllers\ListTemplateController::class . ':updateByUserWithEntityDest');
$app->get('/listTemplates/types/{typeId}/roles', \Entity\controllers\ListTemplateController::class . ':getTypeRoles');
$app->put('/listTemplates/types/{typeId}/roles', \Entity\controllers\ListTemplateController::class . ':updateTypeRoles');
$app->get('/roles', \Entity\controllers\ListTemplateController::class . ':getRoles');

//Circuits
$app->get('/availableCircuits', \Entity\controllers\ListTemplateController::class . ':getAvailableCircuits');
$app->put('/circuits/{type}', \Entity\controllers\ListInstanceController::class . ':updateCircuits');

//Notes
$app->post('/notes', \Note\controllers\NoteController::class . ':create');
$app->get('/notes/{id}', \Note\controllers\NoteController::class . ':getById');
$app->put('/notes/{id}', \Note\controllers\NoteController::class . ':update');
$app->delete('/notes/{id}', \Note\controllers\NoteController::class . ':delete');
$app->get('/notesTemplates', \Note\controllers\NoteController::class . ':getTemplates');

//Parameters
$app->get('/parameters', \Parameter\controllers\ParameterController::class . ':get');
$app->post('/parameters', \Parameter\controllers\ParameterController::class . ':create');
$app->get('/parameters/{id}', \Parameter\controllers\ParameterController::class . ':getById');
$app->put('/parameters/{id}', \Parameter\controllers\ParameterController::class . ':update');
$app->delete('/parameters/{id}', \Parameter\controllers\ParameterController::class . ':delete');

//PasswordRules
$app->get('/passwordRules', \SrcCore\controllers\PasswordController::class . ':getRules');
$app->put('/passwordRules', \SrcCore\controllers\PasswordController::class . ':updateRules');

//Priorities
$app->get('/priorities', \Priority\controllers\PriorityController::class . ':get');
$app->post('/priorities', \Priority\controllers\PriorityController::class . ':create');
$app->get('/priorities/{id}', \Priority\controllers\PriorityController::class . ':getById');
$app->put('/priorities/{id}', \Priority\controllers\PriorityController::class . ':update');
$app->delete('/priorities/{id}', \Priority\controllers\PriorityController::class . ':delete');
$app->get('/sortedPriorities', \Priority\controllers\PriorityController::class . ':getSorted');
$app->put('/sortedPriorities', \Priority\controllers\PriorityController::class . ':updateSort');

//Reports
$app->get('/reports/groups', \Report\controllers\ReportController::class . ':getGroups');
$app->get('/reports/groups/{groupId}', \Report\controllers\ReportController::class . ':getByGroupId');
$app->put('/reports/groups/{groupId}', \Report\controllers\ReportController::class . ':updateForGroupId');

//Resources
$app->post('/resources', \Resource\controllers\ResController::class . ':create');
$app->get('/resources/{resId}', \Resource\controllers\ResController::class . ':getById');
$app->put('/resources/{resId}', \Resource\controllers\ResController::class . ':update');
$app->get('/resources/{resId}/content', \Resource\controllers\ResController::class . ':getFileContent');
$app->get('/resources/{resId}/versionsInformations', \Resource\controllers\ResController::class . ':getVersionsInformations');
$app->get('/resources/{resId}/content/{version}', \Resource\controllers\ResController::class . ':getVersionFileContent');
$app->get('/resources/{resId}/originalContent', \Resource\controllers\ResController::class . ':getOriginalFileContent');
$app->get('/resources/{resId}/thumbnail', \Resource\controllers\ResController::class . ':getThumbnailContent');
$app->get('/resources/{resId}/isAllowed', \Resource\controllers\ResController::class . ':isAllowedForCurrentUser');
$app->get('/resources/{resId}/items', \Resource\controllers\ResController::class . ':getItems');
$app->get('/resources/{resId}/attachments', \Attachment\controllers\AttachmentController::class . ':getByResId');
$app->get('/resources/{resId}/contacts', \Contact\controllers\ContactController::class . ':getByResId');
$app->get('/resources/{resId}/emails', \Email\controllers\EmailController::class . ':getByResId');
$app->get('/resources/{resId}/notes', \Note\controllers\NoteController::class . ':getByResId');
$app->get('/resources/{resId}/templates', \Template\controllers\TemplateController::class . ':getByResId');
$app->get('/resources/{resId}/emailTemplates', \Template\controllers\TemplateController::class . ':getEmailTemplatesByResId');
$app->get('/resources/{resId}/listInstance', \Entity\controllers\ListInstanceController::class . ':getByResId');
$app->get('/resources/{resId}/visaCircuit', \Entity\controllers\ListInstanceController::class . ':getVisaCircuitByResId');
$app->get('/resources/{resId}/opinionCircuit', \Entity\controllers\ListInstanceController::class . ':getOpinionCircuitByResId');
$app->get('/resources/{resId}/parallelOpinion', \Entity\controllers\ListInstanceController::class . ':getParallelOpinionByResId');
$app->get('/resources/{resId}/defaultCircuit', \Entity\controllers\ListTemplateController::class . ':getDefaultCircuitByResId');
$app->get('/resources/{resId}/linkedResources', \Resource\controllers\LinkController::class . ':getLinkedResources');
$app->post('/resources/{resId}/linkedResources', \Resource\controllers\LinkController::class . ':linkResources');
$app->put('/resources/{resId}/sign', \SignatureBook\controllers\SignatureBookController::class . ':signResource');
$app->put('/resources/{resId}/unsign', \SignatureBook\controllers\SignatureBookController::class . ':unsignResource');
$app->get('/resources/{resId}/acknowledgementReceipts', \AcknowledgementReceipt\controllers\AcknowledgementReceiptController::class . ':getByResId');
$app->get('/resources/{resId}/shippings', \Shipping\controllers\ShippingController::class . ':getByResId');
$app->get('/resources/{resId}/messageExchanges', \MessageExchange\controllers\MessageExchangeController::class . ':getByResId');
$app->get('/resources/{resId}/emailsInitialization', \Email\controllers\EmailController::class . ':getInitializationByResId');
$app->get('/resources/{resId}/fields/{fieldId}', \Resource\controllers\ResController::class . ':getField');
$app->delete('/resources/{resId}/linkedResources/{id}', \Resource\controllers\LinkController::class . ':unlinkResources');
$app->delete('/resources/{resId}/circuits/{type}', \Entity\controllers\ListInstanceController::class . ':deleteCircuit');
$app->get('/resources/{resId}/fileInformation', \Resource\controllers\ResController::class . ':getResourceFileInformation');

$app->put('/res/resource/status', \Resource\controllers\ResController::class . ':updateStatus');
$app->post('/res/list', \Resource\controllers\ResController::class . ':getList');
$app->put('/res/externalInfos', \Resource\controllers\ResController::class . ':updateExternalInfos');
$app->get('/categories', \Resource\controllers\ResController::class . ':getCategories');
$app->get('/resources/{resId}/users/{userId}/isDestinationChanging', \Action\controllers\PreProcessActionController::class . ':isDestinationChanging');
$app->get('/resources/{resId}/users/{userId}/groups/{groupId}/baskets/{basketId}/processingData', \Resource\controllers\ResController::class . ':getProcessingData');
$app->post('/resources/folderPrint', \Resource\controllers\FolderPrintController::class . ':generateFile');

//ResourcesList
$app->get('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}', \Resource\controllers\ResourceListController::class . ':get');
$app->get('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions', \Resource\controllers\ResourceListController::class . ':getActions');
$app->put('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/lock', \Resource\controllers\ResourceListController::class . ':lock');
$app->put('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/unlock', \Resource\controllers\ResourceListController::class . ':unlock');
$app->get('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/filters', \Resource\controllers\ResourceListController::class . ':getFilters');
$app->put('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/exports', \Resource\controllers\ExportController::class . ':updateExport');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/summarySheets', \Resource\controllers\SummarySheetController::class . ':createList');
$app->put('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}', \Resource\controllers\ResourceListController::class . ':setAction');
$app->get('/resourcesList/exportTemplate', \Resource\controllers\ExportController::class . ':getExportTemplates');
$app->get('/resourcesList/summarySheets', \Resource\controllers\SummarySheetController::class . ':createListWithAll');
$app->put('/resourcesList/integrations', \Resource\controllers\ResController::class . ':setInIntegrations');

//PreProcess
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkAcknowledgementReceipt', \Action\controllers\PreProcessActionController::class . ':checkAcknowledgementReceipt');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/checkExternalSignatoryBook', \Action\controllers\PreProcessActionController::class . ':checkExternalSignatoryBook');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/checkExternalNoteBook', \Action\controllers\PreProcessActionController::class . ':checkExternalNoteBook');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/checkInitiatorEntity', \Action\controllers\PreProcessActionController::class . ':checkInitiatorEntity');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/checkAttachmentsAndNotes', \Action\controllers\PreProcessActionController::class . ':checkAttachmentsAndNotes');
$app->get('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/getRedirect', \Action\controllers\PreProcessActionController::class . ':getRedirectInformations');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkShippings', \Action\controllers\PreProcessActionController::class . ':checkShippings');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkSignatureBook', \Action\controllers\PreProcessActionController::class . ':checkSignatureBook');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkContinueVisaCircuit', \Action\controllers\PreProcessActionController::class . ':checkContinueVisaCircuit');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkValidateParallelOpinion', \Action\controllers\PreProcessActionController::class . ':checkValidateParallelOpinion');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkContinueOpinionCircuit', \Action\controllers\PreProcessActionController::class . ':checkContinueOpinionCircuit');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkGiveParallelOpinion', \Action\controllers\PreProcessActionController::class . ':checkGiveParallelOpinion');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkRejectVisa', \Action\controllers\PreProcessActionController::class . ':checkRejectVisa');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkInterruptResetVisa', \Action\controllers\PreProcessActionController::class . ':checkInterruptResetVisa');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkCloseWithFieldsAction', \Action\controllers\PreProcessActionController::class . ':checkCloseWithFieldsAction');
$app->post('/resourcesList/users/{userId}/groups/{groupId}/baskets/{basketId}/actions/{actionId}/checkReconcile', \Action\controllers\PreProcessActionController::class . ':checkReconcile');

//Search
$app->get('/search', \Search\controllers\SearchController::class . ':get');

//shipping
$app->get('/administration/shippings', \Shipping\controllers\ShippingTemplateController::class . ':get');
$app->get('/administration/shippings/new', \Shipping\controllers\ShippingTemplateController::class . ':initShipping');
$app->get('/administration/shippings/{id}', \Shipping\controllers\ShippingTemplateController::class . ':getById');
$app->post('/administration/shippings', \Shipping\controllers\ShippingTemplateController::class . ':create');
$app->put('/administration/shippings/{id}', \Shipping\controllers\ShippingTemplateController::class . ':update');
$app->delete('/administration/shippings/{id}', \Shipping\controllers\ShippingTemplateController::class . ':delete');

//SignatureBook
$app->get('/signatureBook/users/{userId}/groups/{groupId}/baskets/{basketId}/resources', \SignatureBook\controllers\SignatureBookController::class . ':getResources');
$app->get('/signatureBook/users/{userId}/groups/{groupId}/baskets/{basketId}/resources/{resId}', \SignatureBook\controllers\SignatureBookController::class . ':getSignatureBook');
$app->get('/signatureBook/{resId}/attachments', \SignatureBook\controllers\SignatureBookController::class . ':getAttachmentsById');
$app->get('/signatureBook/{resId}/incomingMailAttachments', \SignatureBook\controllers\SignatureBookController::class . ':getIncomingMailAndAttachmentsById');

//statuses
$app->get('/statuses', \Status\controllers\StatusController::class . ':get');
$app->post('/statuses', \Status\controllers\StatusController::class . ':create');
$app->get('/statuses/{identifier}', \Status\controllers\StatusController::class . ':getByIdentifier');
$app->get('/status/{id}', \Status\controllers\StatusController::class . ':getById');
$app->put('/statuses/{identifier}', \Status\controllers\StatusController::class . ':update');
$app->delete('/statuses/{identifier}', \Status\controllers\StatusController::class . ':delete');
$app->get('/administration/statuses/new', \Status\controllers\StatusController::class . ':getNewInformations');

//Tags
$app->get('/tags', \Tag\controllers\TagController::class . ':get');
$app->post('/tags', \Tag\controllers\TagController::class . ':create');
$app->get('/tags/{id}', \Tag\controllers\TagController::class . ':getById');
$app->put('/tags/{id}', \Tag\controllers\TagController::class . ':update');
$app->put('/mergeTags', \Tag\controllers\TagController::class . ':merge');
$app->delete('/tags/{id}', \Tag\controllers\TagController::class . ':delete');
$app->put('/tags/{id}/link', \Tag\controllers\TagController::class . ':link');
$app->delete('/tags/{tagId}/link/{id}', \Tag\controllers\TagController::class . ':unLink');

//Templates
$app->get('/templates', \Template\controllers\TemplateController::class . ':get');
$app->post('/templates', \Template\controllers\TemplateController::class . ':create');
$app->get('/templates/{id}/details', \Template\controllers\TemplateController::class . ':getDetailledById');
$app->put('/templates/{id}', \Template\controllers\TemplateController::class . ':update');
$app->delete('/templates/{id}', \Template\controllers\TemplateController::class . ':delete');
$app->post('/templates/{id}/duplicate', \Template\controllers\TemplateController::class . ':duplicate');
$app->get('/administration/templates/new', \Template\controllers\TemplateController::class . ':initTemplates');
$app->post('/templates/{id}/mergeEmail', \Template\controllers\TemplateController::class . ':mergeEmailTemplate');

//Users
$app->get('/users', \User\controllers\UserController::class . ':get');
$app->post('/users', \User\controllers\UserController::class . ':create');
$app->get('/users/{id}', \User\controllers\UserController::class . ':getById');
$app->put('/users/{id}', \User\controllers\UserController::class . ':update');
$app->delete('/users/{id}', \User\controllers\UserController::class . ':delete');
$app->put('/users/{id}/suspend', \User\controllers\UserController::class . ':suspend');
$app->get('/users/{id}/isDeletable', \User\controllers\UserController::class . ':isDeletable');
$app->get('/users/{id}/details', \User\controllers\UserController::class . ':getDetailledById');
$app->put('/users/{id}/password', \User\controllers\UserController::class . ':updatePassword');
$app->get('/users/{userId}/status', \User\controllers\UserController::class . ':getStatusByUserId');
$app->put('/users/{id}/status', \User\controllers\UserController::class . ':updateStatus');
$app->put('/users/{id}/createInMaarchParapheur', \ExternalSignatoryBook\controllers\MaarchParapheurController::class . ':sendUserToMaarchParapheur');
$app->put('/users/{id}/linkToMaarchParapheur', \ExternalSignatoryBook\controllers\MaarchParapheurController::class . ':linkUserToMaarchParapheur');
$app->put('/users/{id}/unlinkToMaarchParapheur', \ExternalSignatoryBook\controllers\MaarchParapheurController::class . ':unlinkUserToMaarchParapheur');
$app->get('/users/{id}/statusInMaarchParapheur', \ExternalSignatoryBook\controllers\MaarchParapheurController::class . ':userStatusInMaarchParapheur');
$app->put('/users/{id}/externalSignatures', \ExternalSignatoryBook\controllers\MaarchParapheurController::class . ':sendSignaturesToMaarchParapheur');
$app->post('/users/{id}/groups', \User\controllers\UserController::class . ':addGroup');
$app->put('/users/{id}/groups/{groupId}', \User\controllers\UserController::class . ':updateGroup');
$app->delete('/users/{id}/groups/{groupId}', \User\controllers\UserController::class . ':deleteGroup');
$app->get('/users/{id}/entities', \User\controllers\UserController::class . ':getEntities');
$app->post('/users/{id}/entities', \User\controllers\UserController::class . ':addEntity');
$app->put('/users/{id}/entities/{entityId}', \User\controllers\UserController::class . ':updateEntity');
$app->put('/users/{id}/entities/{entityId}/primaryEntity', \User\controllers\UserController::class . ':updatePrimaryEntity');
$app->get('/users/{id}/entities/{entityId}', \User\controllers\UserController::class . ':isEntityDeletable');
$app->delete('/users/{id}/entities/{entityId}', \User\controllers\UserController::class . ':deleteEntity');
$app->post('/users/{id}/signatures', \User\controllers\UserController::class . ':addSignature');
$app->get('/users/{id}/signatures/{signatureId}/content', \User\controllers\UserController::class . ':getImageContent');
$app->put('/users/{id}/signatures/{signatureId}', \User\controllers\UserController::class . ':updateSignature');
$app->delete('/users/{id}/signatures/{signatureId}', \User\controllers\UserController::class . ':deleteSignature');
$app->post('/users/{id}/redirectedBaskets', \User\controllers\UserController::class . ':setRedirectedBaskets');
$app->delete('/users/{id}/redirectedBaskets', \User\controllers\UserController::class . ':deleteRedirectedBasket');
$app->put('/users/{id}/baskets', \User\controllers\UserController::class . ':updateBasketsDisplay');
$app->put('/users/{id}/accountActivationNotification', \User\controllers\UserController::class . ':sendAccountActivationNotification');
$app->post('/password', \User\controllers\UserController::class . ':forgotPassword');
$app->put('/password', \User\controllers\UserController::class . ':passwordInitialization');

//UserFollowedResources
$app->post('/resources/follow', \Resource\controllers\UserFollowedResourceController::class . ':follow');
$app->delete('/resources/unfollow', \Resource\controllers\UserFollowedResourceController::class . ':unFollow');
$app->get('/followedResources', \Resource\controllers\UserFollowedResourceController::class . ':getFollowedResources');
$app->get('/followedResources/{resId}/baskets', \Resource\controllers\UserFollowedResourceController::class . ':getBaskets');
$app->get('/followedResources/filters', \Resource\controllers\UserFollowedResourceController::class . ':getFilters');

//VersionsUpdate
$app->get('/versionsUpdate', \VersionUpdate\controllers\VersionUpdateController::class . ':get');
$app->put('/versionsUpdate', \VersionUpdate\controllers\VersionUpdateController::class . ':update');

//CurrentUser
$app->get('/currentUser/profile', \User\controllers\UserController::class . ':getProfile');
$app->put('/currentUser/profile', \User\controllers\UserController::class . ':updateProfile');
$app->put('/currentUser/profile/preferences', \User\controllers\UserController::class . ':updateCurrentUserPreferences');
$app->post('/currentUser/emailSignature', \User\controllers\UserController::class . ':createCurrentUserEmailSignature');
$app->put('/currentUser/emailSignature/{id}', \User\controllers\UserController::class . ':updateCurrentUserEmailSignature');
$app->delete('/currentUser/emailSignature/{id}', \User\controllers\UserController::class . ':deleteCurrentUserEmailSignature');
$app->put('/currentUser/groups/{groupId}/baskets/{basketId}', \User\controllers\UserController::class . ':updateCurrentUserBasketPreferences');
$app->get('/currentUser/templates', \User\controllers\UserController::class . ':getTemplates');
$app->get('/currentUser/emailSignatures', \User\controllers\UserController::class . ':getCurrentUserEmailSignatures');
$app->get('/currentUser/emailSignatures/{id}', \User\controllers\UserController::class . ':getCurrentUserEmailSignatureById');
$app->get('/currentUser/availableEmails', \Email\controllers\EmailController::class . ':getAvailableEmails');

//Notifications
$app->get('/notifications', \Notification\controllers\NotificationController::class . ':get');
$app->post('/notifications', \Notification\controllers\NotificationController::class . ':create');
$app->get('/notifications/schedule', \Notification\controllers\NotificationScheduleController::class . ':get');
$app->post('/notifications/schedule', \Notification\controllers\NotificationScheduleController::class . ':create');
$app->put('/notifications/{id}', \Notification\controllers\NotificationController::class . ':update');
$app->delete('/notifications/{id}', \Notification\controllers\NotificationController::class . ':delete');
$app->get('/administration/notifications/new', \Notification\controllers\NotificationController::class . ':initNotification');
$app->get('/notifications/{id}', \Notification\controllers\NotificationController::class . ':getBySid');
$app->post('/scriptNotification', \Notification\controllers\NotificationScheduleController::class . ':createScriptNotification');

//External MessageExchanges
$app->get('/messageExchanges/{id}', \MessageExchange\controllers\MessageExchangeController::class . ':getById');
$app->delete('/messageExchanges/{id}', \MessageExchange\controllers\MessageExchangeController::class . ':delete');
$app->get('/messageExchanges/{id}/archiveContent', \MessageExchange\controllers\MessageExchangeController::class . ':getArchiveContentById');
$app->post('/saveNumericPackage', \MessageExchange\controllers\ReceiveMessageExchangeController::class . ':saveMessageExchange');
$app->post('/saveMessageExchangeReturn', \MessageExchange\controllers\ReceiveMessageExchangeController::class . ':saveMessageExchangeReturn');
$app->post('/saveMessageExchangeReview', \MessageExchange\controllers\MessageExchangeReviewController::class . ':saveMessageExchangeReview');
$app->post('/resources/{resId}/messageExchange', \MessageExchange\controllers\SendMessageExchangeController::class . ':createMessageExchange');
$app->get('/messageExchangesInitialization', \MessageExchange\controllers\SendMessageExchangeController::class . ':getInitialization');

//ExternalSignatoryBooks
$app->get('/documents/{id}/maarchParapheurWorkflow', \ExternalSignatoryBook\controllers\MaarchParapheurController::class . ':getWorkflow');
$app->get('/maarchParapheur/user/{id}/picture', \ExternalSignatoryBook\controllers\MaarchParapheurController::class . ':getUserPicture');
$app->get('/externalSignatureBooks/enabled', \ExternalSignatoryBook\controllers\ExternalSignatureBookController::class . ':getEnabledSignatureBook');
$app->get('/externalSummary/{resId}', \ExternalSummary\controllers\SummaryController::class . ':getByResId');

$app->get('/externalConnectionsEnabled', \SrcCore\controllers\CoreController::class . ':externalConnectionsEnabled');

// NCH01
$app->get('/getContactByMail', \Contact\controllers\ContactController::class . ':getByMail');
$app->get('/getContactByUrl', \Contact\controllers\ContactController::class . ':getByUrl');
$app->post('/reconciliation/add', \Attachment\controllers\ReconciliationController::class . ':create');
$app->post('/reconciliation/check', \Attachment\controllers\ReconciliationController::class . ':checkAttachment');
$app->get('/getContactByPhone', \Contact\controllers\ContactController::class . ':getByPhone');
// END NCH01


$app->run();
