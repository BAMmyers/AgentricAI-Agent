import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand('agentricai.startChat', () => {
    vscode.window.showInformationMessage('AgentricAI Chat Extension Activated. Use this to execute chat tasks in the AgentricAI ecosystem.');
    // Add logic to invoke the AgentricAI Code Agent or execute operations
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {}