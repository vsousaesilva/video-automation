import { Link } from 'react-router-dom'

export default function TermosDeUso() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm p-8">
        <Link to="/login" className="text-indigo-600 hover:text-indigo-700 text-sm mb-6 inline-block">
          &larr; Voltar
        </Link>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">Termos de Uso</h1>
        <p className="text-sm text-gray-500 mb-8">Ultima atualizacao: 12 de abril de 2026</p>

        <div className="prose prose-gray max-w-none space-y-6">
          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">1. Aceitacao dos Termos</h2>
            <p className="text-gray-600 leading-relaxed">
              Ao acessar e utilizar a plataforma Usina do Tempo ("Plataforma"), voce concorda em cumprir
              e estar sujeito a estes Termos de Uso. Se voce nao concorda com algum dos termos, nao utilize a Plataforma.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">2. Descricao do Servico</h2>
            <p className="text-gray-600 leading-relaxed">
              A Usina do Tempo e uma plataforma SaaS de marketing digital que oferece ferramentas de automacao
              para producao de conteudo, gerenciamento de campanhas publicitarias e relacionamento com clientes,
              utilizando inteligencia artificial como diferencial competitivo.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">3. Cadastro e Conta</h2>
            <p className="text-gray-600 leading-relaxed">
              Para utilizar a Plataforma, voce devera criar uma conta fornecendo informacoes verdadeiras, completas
              e atualizadas. Voce e responsavel por manter a confidencialidade de sua senha e por todas as atividades
              realizadas em sua conta.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">4. Planos e Pagamento</h2>
            <p className="text-gray-600 leading-relaxed">
              A Plataforma oferece diferentes planos de assinatura com niveis distintos de funcionalidades e limites
              de uso. Os pagamentos sao processados pela plataforma Asaas. Ao assinar um plano pago, voce autoriza
              a cobranca recorrente conforme o plano escolhido.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">5. Uso Aceitavel</h2>
            <p className="text-gray-600 leading-relaxed">Voce concorda em nao:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-1 mt-2">
              <li>Utilizar a Plataforma para atividades ilegais ou nao autorizadas</li>
              <li>Violar quaisquer leis aplicaveis, incluindo propriedade intelectual</li>
              <li>Tentar acessar areas restritas ou comprometer a seguranca do sistema</li>
              <li>Revender ou redistribuir o acesso sem autorizacao</li>
              <li>Publicar conteudo ofensivo, difamatorio ou que viole direitos de terceiros</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">6. Propriedade Intelectual</h2>
            <p className="text-gray-600 leading-relaxed">
              O conteudo gerado pelo usuario permanece de propriedade do usuario. A Plataforma, incluindo
              seu codigo-fonte, design, marca e funcionalidades, e propriedade da Usina do Tempo.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">7. Limitacao de Responsabilidade</h2>
            <p className="text-gray-600 leading-relaxed">
              A Plataforma e fornecida "como esta". Nao garantimos que os servicos serao ininterruptos ou
              livres de erros. Nao nos responsabilizamos por danos indiretos decorrentes do uso da Plataforma.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">8. Cancelamento</h2>
            <p className="text-gray-600 leading-relaxed">
              Voce pode cancelar sua assinatura a qualquer momento. O acesso aos recursos do plano pago
              continuara ate o fim do periodo ja pago. Apos o cancelamento, sua conta sera migrada para o plano gratuito.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">9. Alteracoes nos Termos</h2>
            <p className="text-gray-600 leading-relaxed">
              Reservamo-nos o direito de modificar estes Termos a qualquer momento. Alteracoes significativas
              serao comunicadas por email ou notificacao na Plataforma.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">10. Contato</h2>
            <p className="text-gray-600 leading-relaxed">
              Para duvidas sobre estes Termos, entre em contato pelo email:{' '}
              <a href="mailto:suporte@usinadotempo.com.br" className="text-indigo-600 hover:text-indigo-700">
                suporte@usinadotempo.com.br
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
